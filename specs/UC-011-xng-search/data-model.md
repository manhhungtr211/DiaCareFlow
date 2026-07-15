# Data Model: UC-011 XNG Search & Web Scraper

**Feature**: Tìm kiếm và trích xuất nội dung web  
**Phase**: 1 — Design  
**Date**: 2026-07-15  
**Revision**: v2 — Updated per user edits (2026-07-15)

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base class | `pydantic.BaseModel` (thống nhất toàn bộ) | Validation tự động, serializable to JSON, tương thích FastAPI. Bỏ `@dataclass`. |
| `ScoredURL` hierarchy | Kế thừa `SearchResult` | `ScoredURL` IS-A `SearchResult` + thêm scoring fields |
| `SearchQuery` type | `@dataclass` | Input schema thuần túy, không cần validation |
| `ScrapedContent` | Giữ lại như entity riêng | Output của Crawl4ai cần tracked per-URL (AC-5 requires per-URL error isolation) |

---

## Core Entities

### 1. `SearchQuery` — Tham số gọi XNG Search API

```python
@dataclass
class SearchQuery(total=False):
    query: str                    # (required) Câu hỏi/từ khóa tìm kiếm
    language: str | None          # Ngôn ngữ (vd: "vi", "en"), mặc định None
    pagenum: int | None           # Trang kết quả, mặc định 1
    time_range: str | None        # Khoảng thời gian ("day", "week", "month", "year")
    safe_search: int | None       # 0=off, 1=moderate, 2=strict
```

**Ghi chú**: `total=False` → tất cả fields ngoài `query` là optional.

---

### 2. `SearchResult` — Kết quả từ XNG Search API

```python
class SearchResult(BaseModel):
    url: str                      # URL của kết quả
    title: str                    # Tiêu đề trang
    content: str                  # Đoạn mô tả/snippet từ XNG
    weight: float                 # Trọng số từ XNG (item.score), range [0, 1]
    publishedDate: str | None = None  # Ngày xuất bản (nếu có)
    engine: str = ""              # Search engine nguồn (google, bing, ...)

    @validator("weight")
    def clamp_weight(cls, v):
        return max(0.0, min(1.0, v))
```

**Validation**:
- `url`: non-empty, valid HTTP/HTTPS URL.
- `weight`: clamped to [0.0, 1.0] via validator.
- `publishedDate`: ISO 8601 string hoặc `None`.
- `engine`: có thể empty string (fallback nếu XNG không trả về).

---

### 3. `ScoredURL` — URL sau khi qua thuật toán ranking

```python
class ScoredURL(SearchResult):
    freq_boost: float = 0.0         # Điểm từ item.weight (tần suất XNG)
    hostname_boost: float = 0.0     # Điểm từ trusted domain check
    path_boost: float = 0.0         # Điểm từ URL path depth decay
    jina_rerank_boost: float = 0.0  # Điểm từ Jina AI reranker (0.0 nếu API unavailable)
    final_score: float = 0.0        # Tổng điểm sau clamp [0.0, 5.0]
```

**State Transition**:
```
SearchResult → [Ranker/Scorer] → ScoredURL
ScoredURL × N (sorted desc by final_score) → top-3 selected
```

**Score formula**:
```
raw = hostname_boost + path_boost + freq_boost + jina_rerank_boost
final_score = clamp(raw, 0.0, 5.0)
```

---

### 4. `ScrapedContent` — Nội dung đã scrape từ một URL

```python
class ScrapedContent(BaseModel):
    url: str                  # URL đã scrape
    markdown: str = ""        # Nội dung dạng markdown (từ Crawl4ai)
    success: bool             # True nếu scrape thành công
    error: str | None = None  # Thông báo lỗi nếu thất bại (AC-5)
```

**States**:
- `success=True, markdown=<non-empty>`: Scrape thành công
- `success=False, error=<msg>`: Bị chặn bot / lỗi 404 / timeout (AC-5 — hệ thống không crash)
- `success=True, markdown=""`: Trang không có nội dung text (ít xảy ra)

---

### 5. `WebSearchResponse` — Kết quả tổng hợp cuối cùng

```python
class WebSearchResponse(BaseModel):
    query: str                              # Câu hỏi/từ khóa gốc
    result: list[SearchResult]              # Danh sách raw từ XNG (tối đa 5)
    scored_result: list[ScoredURL]          # Danh sách sau ranking (top-3)
    scraped_contents: list[ScrapedContent]  # Nội dung đã scrape (per-URL)
    combined_text: str = ""                 # Nội dung tổng hợp để trả về người dùng
    found: bool = True                      # False nếu XNG trả về 0 results (AC-4)
    error: str | None = None                # Lỗi hệ thống nếu có (vd: XNG timeout)
```

---

### 6. `RankingConfig` — Cấu hình thuật toán ranking

```python
class RankingConfig(BaseModel):
    host_name_weight: float = 0.4
    path_boost_weight: float = 0.2
    freq_weight: float = 0.3
    jina_weight: float = 0.1
    trusted_multiplier: float = 2.0   # AC-2: multiplier cho trusted domain
    decay_factor: float = 0.8         # AC-3: decay per path depth level
    top_k: int = 5                    # URLs lấy từ XNG
    scrape_top_n: int = 3             # URLs đem scrape sau ranking
    score_min: float = 0.0
    score_max: float = 5.0
```

---

## Data Flow

```
SearchQuery (input)
    │
    ▼
[XNG Search API]
    │
    └──► SearchResult × top_k (≤5)
              │
              ▼
        [Ranker / Scorer]
         ├── hostname_boost  (trusted domain × multiplier)
         ├── path_boost      (URL depth decay: 0.8^(depth-1))
         ├── freq_boost      (item.weight × freq_weight)
         └── jina_rerank_boost (Jina API, graceful degrade)
              │
              ▼
        ScoredURL × top_k (sorted desc by final_score)
              │
         top-3 selected
              │
              ▼
        [Crawl4ai Scraper × 3 parallel]
              │
              ├── ScrapedContent (success=True)   ─┐
              ├── ScrapedContent (success=False)    │ → isolated per AC-5
              └── ScrapedContent (success=True)   ─┘
              │
              ▼
        [Aggregator]
        combined_text = join(successful markdowns)
              │
              ▼
        WebSearchResponse
```

---

## Validation Rules

| Field | Rule |
|-------|------|
| `SearchResult.url` | Non-empty, starts with `http://` or `https://` |
| `SearchResult.weight` | Clamped to [0.0, 1.0] |
| `ScoredURL.final_score` | Clamped to [0.0, 5.0] |
| `ScrapedContent.markdown` | May be empty string if page has no text |
| `RankingConfig.decay_factor` | [0.0, 1.0] |
| `RankingConfig.trusted_multiplier` | ≥ 1.0 |
| `WebSearchResponse.found` | False only when `result` is empty list |

---

## Trusted Domains Config (External)

File: `src/tools/web/config/trusted_domains.yaml`

```yaml
trusted_domains:
  - vndiabetes.org
  - diabetes.org
  - who.int
  - ncbi.nlm.nih.gov
  - pubmed.ncbi.nlm.nih.gov
  - mayoclinic.org
  - healthline.com
  - webmd.com
  - suckhoedoisong.vn
  - vinmec.com
```

Loaded once at startup. Accessible via `TrustedDomainRegistry` singleton.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `XNG_SEARCH_URL` | Yes | — | Base URL của SearXNG instance (e.g. `http://localhost:8080`) |
| `XNG_MAX_RESULTS` | No | `5` | Số kết quả tối đa lấy từ XNG |
| `JINA_API_KEY` | No | — | Jina AI key (đã có trong `.env`). Nếu không có → `jina_rerank_boost=0.0` |
| `SCRAPE_TIMEOUT` | No | `10` | Timeout (seconds) per URL cho Crawl4ai |
| `TRUSTED_DOMAINS_PATH` | No | `src/tools/web/config/trusted_domains.yaml` | Path đến file trusted domains |
