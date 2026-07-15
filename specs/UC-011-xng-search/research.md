# Research: UC-011 XNG Search & Web Scraper

**Feature**: Tìm kiếm và trích xuất nội dung web (XNG Search & Scrape)
**Date**: 2026-07-15
**Status**: Complete

---

## 1. XNG Search API Integration

### Decision
Sử dụng thư viện `httpx` (đã có trong requirements.txt) để gọi XNG Search API qua HTTP, hoặc tích hợp SDK `searxng-client` nếu cần. Cấu hình endpoint via biến môi trường `XNG_SEARCH_URL` (Docker host URL).

### Rationale
- `httpx` async-capable và đã có sẵn, tránh thêm dependency không cần thiết.
- XNG Search (SearXNG) expose REST API tại `/search?q=...&format=json` — dễ gọi qua HTTP.
- Trả về JSON với field `results[].url`, `results[].score` (weight), `results[].title`, `results[].content`.

### Key API Fields
```json
{
  "results": [
    {
      "url": "https://example.com/article",
      "title": "...",
      "content": "...",
      "publishedDate": "...",
      "score": 0.95,  # Score from SearXNG engine
      "engine": "google"
    }
  ]
}
```

### Alternatives Considered
- `searxng-client` SDK: Thêm dependency, ít linh hoạt hơn custom httpx call.
- `requests`: Synchronous, không phù hợp với async context của FastAPI.

---

## 2. Crawl4ai Integration

### Decision
Sử dụng `crawl4ai` Python package với `AsyncWebCrawler` (async mode). Cài thêm `crawl4ai` vào `requirements.txt`.

### Rationale
- Crawl4ai cung cấp `AsyncWebCrawler` với built-in anti-bot bypass (stealth mode, user-agent rotation).
- Hỗ trợ `arun()` async per-URL, dễ wrap trong `asyncio.gather()` để scrape top-3 song song.
- Output markdown-formatted text từ HTML (`.result.markdown`) — clean và dễ dùng cho LLM.

### Key Usage Pattern
```python
from crawl4ai import AsyncWebCrawler

async def scrape_url(url: str) -> str:
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        return result.markdown if result.success else ""
```

### Alternatives Considered
- `playwright` + BeautifulSoup: Cần setup browser, nặng hơn.
- `requests-html`: Không async-native, deprecated.
- `scrapy`: Quá heavy cho single-URL scraping use case.

---

## 3. Ranking Algorithm Implementation

### Decision
Implement thuật toán ranking như mô tả trong spec với 4 scoring components. Sử dụng `dataclasses` và pure Python cho scoring logic (testable, no external deps).

### Algorithm Details

```python
# Scoring weights (configurable via config.py hoặc constants)
WEIGHTS = {
    "host_name":  0.4,   # Độ uy tín tên miền
    "path_boost": 0.2,   # Độ sâu URL
    "freq":       0.3,   # Tần suất (item.weight từ XNG)
    "jina":       0.1,   # Jina AI score
}
TRUSTED_MULTIPLIER = 2.0
DECAY_FACTOR = 0.8       # decayed_boost cho path depth

# Scoring formula:
# host_score    = host_freq * multiplier * WEIGHTS["host_name"]
# path_score    = sum(prefix_freq * (DECAY_FACTOR^(depth-1)) for depth) * WEIGHTS["path_boost"]
# freq_score    = item.weight * WEIGHTS["freq"]
# jina_score    = jina_rating * WEIGHTS["jina"]
# raw_total     = host_score + path_score + freq_score + jina_score
# final_score   = clamp(raw_total, 0, 5)
```

### Path Boost Logic
```
URL: "https://vndiabetes.org/articles/diet/low-glycemic"
path segments: ["articles", "diet", "low-glycemic"]
depth 1: prefix="articles"        → decayed_boost = 0.8^0 = 1.0
depth 2: prefix="articles/diet"   → decayed_boost = 0.8^1 = 0.8
depth 3: prefix="articles/diet/low-glycemic" → decayed_boost = 0.8^2 = 0.64
path_score = sum(prefix_freq_i * decayed_boost_i) * weight
```

### Alternatives Considered
- BM25-based ranking: Overkill, không có full text corpus at search time.
- ML ranking model: Quá phức tạp cho phase 1.

---

## 4. Jina AI Reranker

### Decision
Sử dụng Jina AI Reranker API (đã có `JINA_API_KEY` trong `.env`) để lấy `jina_score` cho mỗi URL. Endpoint: `https://r.jina.ai/{url}` hoặc Reranker API.

### Rationale
- JINA_API_KEY đã configured trong project (`.env` line 12).
- Jina Reader API (`https://r.jina.ai/{url}`) trả về cleaned content + relevance score.
- Có thể dùng Jina Reranker API để rank URLs theo query.

### Key Note
Jina score là optional enrichment. Nếu Jina API fail → jina_score = 0 (graceful degrade, không làm crash ranking).

### Alternatives Considered
- Cohere Reranker: Cần thêm API key mới.
- Cross-encoder local: Tốn resource, cần model download.

---

## 5. Trusted Domains Configuration

### Decision
Store danh sách trusted domains trong file YAML/JSON: `src/tools/web/config/trusted_domains.yaml`. Load once at module import (singleton). Configurable path via env var `TRUSTED_DOMAINS_PATH`.

### Format
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
```

### Alternatives Considered
- Hardcode in Python: Không flexible, khó update.
- Database table: Overkill cho read-only config list.

---

## 6. Async Architecture

### Decision
Tất cả các hàm trong `src/tools/web/` implement với `async/await` pattern, sử dụng `asyncio.gather()` cho parallel scraping của top-3 URLs.

### Rationale
- Crawl4ai native async.
- httpx hỗ trợ `AsyncClient`.
- Parallel scraping of 3 URLs tiết kiệm thời gian đáng kể (3x sequential → ~1x parallel).
- FastAPI cũng async-native, tương thích hoàn hảo.

---

## 7. Module Structure

### Decision
```
src/tools/web/
├── __init__.py
├── search/
│   ├── __init__.py
│   └── xng_search.py        # XNG Search API client
└── ├── ranking/
        ├── __init__.py
        └── scorer.py            # Ranking algorithm
├── scraper/
│   ├── __init__.py
│   └── crawl4ai_scraper.py  # Crawl4ai async scraper
└── config/
    ├── __init__.py
    └── trusted_domains.yaml # Trusted domains list
```

### Rationale
- Tách biệt search / scraping  → dễ test riêng từng module.
---

## 8. Error Handling Strategy

| Error Case | Handling |
|-----------|----------|
| XNG API timeout/500 | Raise `SearchError`, propagate với message thân thiện |
| XNG returns 0 results | Return empty list, caller trả về "Không tìm thấy" |
| Crawl4ai URL blocked | Log warning, skip URL, continue với remaining |
| Jina API failure | jina_score = 0.0, log warning, continue |
| All 3 URLs fail scrape | Return partial result (empty string) với log error |

---

## 9. Testing Strategy

### Unit Tests
- `test_scorer.py`: Test từng formula component (host_name, path_boost, freq, jina).
- `test_xng_search.py`: Mock httpx calls, test response parsing.
- `test_crawl4ai_scraper.py`: Mock AsyncWebCrawler, test error handling.

### Integration Tests
- `test_web_pipeline_integration.py`: End-to-end với real XNG Search (local Docker).

### Key Test Cases (from AC)
- AC-2: URL trusted domain → multiplier=2, score > non-trusted equivalent.
- AC-3: path_boost depth 1 = 1.0, depth 2 = 0.8.
- AC-4: 0 results → no ranking/scraping called.
- AC-5: 1 scrape failure → other 2 still returned, no exception.

---

## 10. Dependencies to Add

```
crawl4ai>=0.4.0
pyyaml>=6.0.0
```

Note: `httpx` already in requirements.txt.
