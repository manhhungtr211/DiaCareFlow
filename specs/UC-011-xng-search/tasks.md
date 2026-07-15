# Tasks: UC-011 XNG Search & Web Scraper

**Input**: Design documents from `specs/UC-011-xng-search/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [data-model.md](./data-model.md) · [contracts/web_search.md](./contracts/web_search.md) · [research.md](./research.md) · [quickstart.md](./quickstart.md)

**Scope**: Standalone Python tool module — `src/tools/web/`. Không tích hợp vào Agent graph trong UC này.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Có thể chạy song song (file khác nhau, không phụ thuộc nhau)
- **[Story]**: User story tương ứng (US1–US5, map từ AC trong spec.md)
- Mỗi task phải có đường dẫn file cụ thể

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Tạo cấu trúc thư mục, cài dependency, cấu hình môi trường

- [ ] T001 Tạo cấu trúc thư mục `src/tools/web/` với các sub-package: `search/`, `scraper/`, `ranking/`, `config/` — mỗi folder cần file `__init__.py`
- [ ] T002 Thêm `crawl4ai>=0.4.0` và `pyyaml>=6.0.0` vào `requirements.txt`
- [ ] T003 [P] Chạy `playwright install chromium` để setup Crawl4ai browser (một lần, ghi vào README)
- [ ] T004 [P] Thêm env vars `XNG_SEARCH_URL`, `XNG_MAX_RESULTS`, `SCRAPE_TIMEOUT` vào `.env.example`
- [ ] T005 [P] Cập nhật `src/config.py` — thêm `XNG_SEARCH_URL`, `XNG_MAX_RESULTS`, `SCRAPE_TIMEOUT` constants

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Các entity và config dùng chung — PHẢI hoàn thành trước khi implement user story bất kỳ

**⚠️ CRITICAL**: Không có user story nào có thể bắt đầu trước khi phase này xong

- [ ] T006 Tạo tất cả Pydantic models trong `src/tools/web/models.py`: `SearchQuery`, `SearchResult`, `ScoredURL`, `ScrapedContent`, `WebSearchResponse`, `RankingConfig` — theo đúng data-model.md
- [ ] T007 [P] Định nghĩa custom exceptions `SearchError` và `ScrapeError` trong `src/tools/web/exceptions.py`
- [ ] T008 [P] Tạo file trusted domains `src/tools/web/config/trusted_domains.yaml` với danh sách 10 domains y khoa từ data-model.md
- [ ] T009 Implement `TrustedDomainRegistry` singleton trong `src/tools/web/config/__init__.py` — load YAML một lần, expose `is_trusted(hostname: str) -> bool`

**Checkpoint**: Models, exceptions, trusted domain config đã sẵn sàng — có thể bắt đầu implement user stories

---

## Phase 3: US1 — XNG Search Client (AC-1, AC-4) 🎯 MVP

**Goal**: Gọi SearXNG API và parse kết quả trả về thành danh sách `SearchResult`

**Independent Test**:
```bash
# Với SearXNG Docker đang chạy:
python -c "
import asyncio
from src.tools.web.search.xng_search import search_xng
results = asyncio.run(search_xng('bệnh tiểu đường'))
print(f'Got {len(results)} results')
assert len(results) > 0
"
```

### Implementation for US1

- [ ] T010 [US1] Implement `search_xng()` async function trong `src/tools/web/search/xng_search.py`:
  - Gọi `GET {XNG_SEARCH_URL}/search?q={query}&format=json`
  - Parse response JSON → `list[SearchResult]`
  - Map fields: `url`, `title`, `content`, `score→weight`, `publishedDate`, `engine`
  - Raise `SearchError` khi HTTP 5xx hoặc connection error
  - Return `[]` khi response 200 nhưng `results` rỗng (AC-4)
- [ ] T011 [US1] Viết unit test `tests/unit/tools/web/test_xng_search.py`:
  - Mock `httpx.AsyncClient.get` — test happy path parse
  - Test khi response trả về `results: []` → return `[]`
  - Test khi HTTP 500 → raise `SearchError`

**Checkpoint**: `search_xng()` hoạt động, mock tests pass — US1 done

---

## Phase 4: US2 — Ranking Algorithm (AC-2, AC-3)

**Goal**: Score và sort URLs bằng composite formula; `ScoredURL.final_score` clamped [0, 5]

**Independent Test**:
```bash
python -c "
from src.tools.web.ranking.scorer import rank_urls
from src.tools.web.models import SearchResult, RankingConfig
results = [
    SearchResult(url='https://diabetes.org/a', title='T', content='', weight=0.5),
    SearchResult(url='https://unknown.com/b', title='T', content='', weight=0.5),
]
scored = rank_urls(results, RankingConfig())
assert scored[0].url == 'https://diabetes.org/a'  # trusted domain ranks first
assert scored[0].hostname_boost > scored[1].hostname_boost
print('AC-2 OK:', scored[0].final_score, '>', scored[1].final_score)
"
```

### Implementation for US2

- [ ] T012 [P] [US2] Implement `compute_hostname_boost(url: str, config: RankingConfig) -> float` trong `src/tools/web/ranking/scorer.py`:
  - Dùng `TrustedDomainRegistry.is_trusted()` để check hostname
  - Trusted: `1.0 * config.trusted_multiplier * config.host_name_weight`
  - Non-trusted: `1.0 * 1.0 * config.host_name_weight`
- [ ] T013 [P] [US2] Implement `compute_path_boost(url: str, config: RankingConfig) -> float` trong `src/tools/web/ranking/scorer.py`:
  - Parse URL path bằng `urllib.parse.urlparse`
  - Tách path thành segments, tính `sum(1 * decay^(i) for i, seg in enumerate(segments))`
  - Nhân với `config.path_boost_weight`
  - AC-3: depth 1 → `decay^0 = 1.0`, depth 2 → `decay^1 = 0.8`
- [ ] T014 [P] [US2] Implement `compute_freq_boost(weight: float, config: RankingConfig) -> float` trong `src/tools/web/ranking/scorer.py`:
  - `return weight * config.freq_weight`
- [ ] T015 [US2] Implement hàm `rank_urls(results, config) -> list[ScoredURL]` trong `src/tools/web/ranking/scorer.py` (depends on T012–T014):
  - Với mỗi `SearchResult`, tạo `ScoredURL` với đủ 4 boost fields
  - `raw = hostname_boost + path_boost + freq_boost + jina_rerank_boost`
  - `final_score = clamp(raw, config.score_min, config.score_max)`
  - Sort giảm dần theo `final_score`, return list
- [ ] T016 [US2] Viết unit test `tests/unit/tools/web/test_scorer.py` (no network):
  - Test AC-2: trusted domain → `hostname_boost` gấp đôi so với non-trusted
  - Test AC-3: `path_boost` depth 1 > depth 2
  - Test clamp: `final_score` không vượt quá 5.0
  - Test sort: list trả về đúng thứ tự giảm dần

**Checkpoint**: `rank_urls()` hoạt động, unit tests AC-2 và AC-3 pass — US2 done

---

## Phase 5: US3 — Jina AI Reranker (AC-2 enhancement)

**Goal**: Lấy `jina_rerank_boost` từ Jina AI API; graceful degrade về `0.0` khi không có API key

**Independent Test**:
```bash
python -c "
import asyncio
from src.tools.web.ranking.jina_reranker import compute_jina_boost
# Test graceful degrade khi không có key
score = asyncio.run(compute_jina_boost('https://diabetes.org', api_key=None))
assert score == 0.0
print('Graceful degrade OK')
"
```

### Implementation for US3

- [ ] T017 [US3] Implement `compute_jina_boost(url: str, api_key: str | None) -> float` trong `src/tools/web/ranking/jina_reranker.py`:
  - Nếu `api_key` là `None` hoặc rỗng → return `0.0` (graceful degrade)
  - Gọi Jina Reader API: `GET https://r.jina.ai/{url}` với header `Authorization: Bearer {api_key}`
  - Parse response score, return `score * config.jina_weight`
  - Bọc trong try/except: mọi lỗi HTTP/network → log warning, return `0.0`
- [ ] T018 [US3] Cập nhật `rank_urls()` trong `src/tools/web/ranking/scorer.py` để inject `jina_rerank_boost`:
  - Gọi `compute_jina_boost()` per URL (có thể batch nếu Jina hỗ trợ)
  - Đưa kết quả vào `ScoredURL.jina_rerank_boost`
- [ ] T019 [US3] Viết unit test `tests/unit/tools/web/test_jina_reranker.py`:
  - Mock `httpx.AsyncClient.get` — test score parse
  - Test `api_key=None` → return `0.0`
  - Test exception handling → return `0.0` (không raise)

**Checkpoint**: `jina_rerank_boost` được tính, fallback an toàn khi API không available — US3 done

---

## Phase 6: US4 — Crawl4ai Scraper (AC-1, AC-5)

**Goal**: Scrape top-3 URLs song song; lỗi 1 URL không crash hệ thống

**Independent Test**:
```bash
python -c "
import asyncio
from unittest.mock import patch, AsyncMock
from src.tools.web.scraper.crawl4ai_scraper import scrape_urls

# AC-5: 1 URL fail, 2 URL thành công
async def run():
    with patch('crawl4ai.AsyncWebCrawler') as mock:
        # ... mock setup
        results = await scrape_urls(['https://url-a.com', 'https://url-b.com', 'https://url-c.com'])
        assert len(results) == 3
        successful = [r for r in results if r.success]
        print(f'Successful: {len(successful)}/3')
asyncio.run(run())
"
```

### Implementation for US4

- [ ] T020 [US4] Implement `scrape_single_url(url: str, timeout: int) -> ScrapedContent` trong `src/tools/web/scraper/crawl4ai_scraper.py`:
  - Dùng `AsyncWebCrawler(verbose=False)` context manager
  - Gọi `crawler.arun(url=url)`
  - Thành công: return `ScrapedContent(url=url, markdown=result.markdown, success=True)`
  - Exception bất kỳ: return `ScrapedContent(url=url, markdown="", success=False, error=str(e))` + log warning (AC-5)
- [ ] T021 [US4] Implement `scrape_urls(urls: list[str], timeout: int = 10) -> list[ScrapedContent]` trong `src/tools/web/scraper/crawl4ai_scraper.py`:
  - Dùng `asyncio.gather(*[scrape_single_url(url, timeout) for url in urls])`
  - Return list giữ nguyên thứ tự input
- [ ] T022 [US4] Viết unit test `tests/unit/tools/web/test_crawl4ai_scraper.py`:
  - Mock `AsyncWebCrawler` — test happy path
  - Test AC-5: 1 URL raise exception → `ScrapedContent(success=False)`, không raise, 2 URL còn lại vẫn return

**Checkpoint**: `scrape_urls()` hoạt động, AC-5 test pass — US4 done

---

## Phase 7: US5 — Public API Orchestrator (AC-1, AC-4)

**Goal**: Gắn kết toàn bộ pipeline thành `web_search()` public function; trả đúng `WebSearchResponse`

**Independent Test** (End-to-end với mocks):
```bash
python -c "
import asyncio
from unittest.mock import patch, AsyncMock
from src.tools.web import web_search

async def run():
    with patch('src.tools.web.search.xng_search.search_xng') as mock_search, \
         patch('src.tools.web.scraper.crawl4ai_scraper.scrape_urls') as mock_scrape:
        from src.tools.web.models import SearchResult, ScrapedContent
        mock_search.return_value = [
            SearchResult(url='https://diabetes.org/a', title='T', content='', weight=0.8),
        ]
        mock_scrape.return_value = [
            ScrapedContent(url='https://diabetes.org/a', markdown='Content', success=True),
        ]
        resp = await web_search('tiểu đường')
        assert resp.found == True
        assert 'Content' in resp.combined_text
        print('AC-1 OK:', resp.combined_text[:50])

asyncio.run(run())
"
```

### Implementation for US5

- [ ] T023 [US5] Implement `web_search(query: str) -> WebSearchResponse` trong `src/tools/web/__init__.py`:
  - Step 1: `results = await search_xng(query, max_results=XNG_MAX_RESULTS)`
  - Step 2: Nếu `results` rỗng → return `WebSearchResponse(query=query, result=[], scored_result=[], ..., found=False)` (AC-4)
  - Step 3: `scored = rank_urls(results, RankingConfig())`
  - Step 4: Lấy top `scrape_top_n=3` từ `scored`
  - Step 5: `scraped = await scrape_urls([s.url for s in top3], timeout=SCRAPE_TIMEOUT)`
  - Step 6: `combined_text = "\n\n".join(c.markdown for c in scraped if c.success and c.markdown)`
  - Step 7: Return `WebSearchResponse(query=query, result=results, scored_result=top3, scraped_contents=scraped, combined_text=combined_text, found=True)`
- [ ] T024 [US5] Thêm logging tại mỗi bước trong `web_search()` (query, num results, top URLs, scrape success count)
- [ ] T025 [US5] Viết unit test `tests/unit/tools/web/test_web_search_pipeline.py` với full mock:
  - Test AC-1 happy path (3 scraped)
  - Test AC-4: `search_xng` returns `[]` → `found=False`, no rank/scrape called
  - Test AC-5: 1 scrape fails → `found=True`, `combined_text` từ 2 URL còn lại

**Checkpoint**: `web_search()` hoạt động end-to-end, tất cả AC pass với mocks — US5 done

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integration test, docs, và validate toàn bộ quickstart scenarios

- [ ] T026 [P] Viết integration test `tests/integration/test_web_search_integration.py` — chỉ chạy khi SearXNG Docker available (dùng `pytest.mark.integration`)
- [ ] T027 [P] Cập nhật `README.md` — thêm section "Web Search Tool" với hướng dẫn setup SearXNG Docker
- [ ] T028 Chạy toàn bộ quickstart scenarios từ `specs/UC-011-xng-search/quickstart.md` và xác nhận pass
- [ ] T029 [P] Cập nhật `src/tools/web/config/trusted_domains.yaml` — review và bổ sung thêm domain y tế Việt Nam nếu cần

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Bắt đầu ngay — không phụ thuộc gì
- **Phase 2 (Foundational)**: Sau Phase 1 — **block toàn bộ user stories**
- **Phase 3–7 (User Stories)**: Sau Phase 2 — có thể chạy theo thứ tự ưu tiên
  - US1 → US2 nên chạy trước US5 (US5 dùng output của US1 và US2)
  - US3 (Jina) độc lập, có thể song song với US2 sau khi Phase 2 xong
  - US4 (Scraper) độc lập, có thể song song với US1–US3
- **Phase 8 (Polish)**: Sau khi tất cả user stories xong

### User Story Dependencies

| Story | Depends On | Blocks |
|-------|-----------|--------|
| US1 (XNG Search) | Phase 2 | US5 |
| US2 (Ranking) | Phase 2, T009 (TrustedDomainRegistry) | US5 |
| US3 (Jina) | US2 (T015) | US5 |
| US4 (Scraper) | Phase 2 | US5 |
| US5 (Orchestrator) | US1, US2, US4 | Phase 8 |

### Parallel Opportunities

```
Phase 2 complete → Start in parallel:
  ├── US1: T010–T011 (XNG Search)
  ├── US2: T012–T014 → T015–T016 (Ranking — T012/T013/T014 parallel, T015 waits)
  ├── US3: T017–T019 (Jina — sau khi T015 xong)
  └── US4: T020–T022 (Scraper)
          │
          └── All US1+US2+US4 done → US5: T023–T025 (Orchestrator)
                                            │
                                            └── Phase 8: T026–T029
```

---

## Parallel Example: Phase 2 → Phase 3+4 Concurrent

```
# Sau khi Phase 2 hoàn thành (T006–T009):

Track A (US1 — XNG):      T010 → T011
Track B (US2 — Ranking):  T012 + T013 + T014 (parallel) → T015 → T016
Track C (US4 — Scraper):  T020 → T021 → T022

# Sau khi Track A + B + C xong:
Track D (US5 — Orchestrator): T023 → T024 → T025
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US4 + US5)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — models, exceptions, trusted domains
3. Complete US1: XNG Search client (T010–T011)
4. Complete US2: Ranking without Jina (T012–T016, set `jina_rerank_boost=0.0`)
5. Complete US4: Scraper (T020–T022)
6. Complete US5: Orchestrator (T023–T025)
7. **STOP và VALIDATE**: Chạy quickstart AC-1, AC-4, AC-5 — tất cả phải pass
8. **MVP Done** — `web_search()` hoạt động end-to-end

### Incremental Delivery

1. MVP (US1+US2+US4+US5) → Test → Demo
2. Thêm US3 (Jina reranker) → Ranking chất lượng hơn → Demo
3. Phase 8 Polish → Integration tests → Production ready

---

## Notes

- `[P]` = tasks trên file khác nhau, không block nhau
- `[Story]` label map từng task về AC tương ứng trong spec.md
- US3 (Jina) là optional enhancement — không cần để US5 hoạt động
- `jina_rerank_boost` gracefully defaults to `0.0` khi Jina API không available
- Tất cả network calls phải có timeout để không block vô hạn
- Commit sau mỗi phase checkpoint
