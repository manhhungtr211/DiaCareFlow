# Quickstart & Validation Guide: UC-011 XNG Search & Scraper

**Feature**: Tìm kiếm và trích xuất nội dung web  
**Date**: 2026-07-15

---

## Prerequisites

### 1. Start SearXNG (Docker)
```bash
# Pull and run SearXNG locally
docker run -d --name searxng -p 8080:8080 searxng/searxng:lastest

# Verify it's running
curl "http://localhost:8080/search?q=diabetes+diet&format=json" | python -m json.tool
```

### 2. Install new dependencies
```bash
pip install crawl4ai pyyaml

# Install Playwright browsers for Crawl4ai (one-time setup)
playwright install chromium
```

### 3. Configure environment
Add to `.env`:
```env
XNG_SEARCH_URL=http://localhost:8080
XNG_MAX_RESULTS=5
SCRAPE_TIMEOUT=10
```

### 4. Verify Jina API key
`JINA_API_KEY` already set in `.env`. If not present, jina_score defaults to 0 (non-blocking).

---

## Module Structure (Expected after implementation)

See [data-model.md](./data-model.md) for entity definitions and [contracts/web_search.md](./contracts/web_search.md) for API contracts.

```
src/tools/web/
├── __init__.py
├── search/
│   ├── __init__.py
│   └── xng_search.py
├── scraper/
│   ├── __init__.py
│   └── crawl4ai_scraper.py
├── ranking/
│   ├── __init__.py
│   └── scorer.py
└── config/
    ├── __init__.py
    └── trusted_domains.yaml
```

---

## Validation Scenarios

### Scenario 1: Happy Path (AC-1)

**Setup**: SearXNG running at `http://localhost:8080`

```python
# Run from project root
import asyncio
from src.tools.web import web_search

async def test_happy_path():
    result = await web_search("bệnh tiểu đường type 2 là gì")
    assert result.found == True
    assert len(result.top_urls) <= 3
    assert len(result.scraped_contents) > 0
    assert result.combined_text != ""
    print(f"✅ Found {len(result.top_urls)} URLs")
    print(f"✅ Combined text length: {len(result.combined_text)} chars")

asyncio.run(test_happy_path())
```

**Expected**: 3 URLs ranked and scraped, `combined_text` non-empty.

---

### Scenario 2: Trusted Domain Gets Higher Score (AC-2)

```python
# Unit test — no network needed
from src.tools.web.ranking.scorer import rank_urls, RankingConfig
from src.tools.web.search.xng_search import SearchResult

results = [
    SearchResult(url="https://diabetes.org/article", title="T1", content="", weight=0.5, engine="test"),
    SearchResult(url="https://unknown-blog.com/post", title="T2", content="", weight=0.5, engine="test"),
]
config = RankingConfig()
scored = rank_urls(results, config)

assert scored[0].url == "https://diabetes.org/article"  # trusted domain ranks first
assert scored[0].score_breakdown["host_name"] > scored[1].score_breakdown["host_name"]
print("✅ AC-2: Trusted domain multiplier=2 verified")
```

---

### Scenario 3: Path Boost Decay (AC-3)

```python
from src.tools.web.ranking.scorer import compute_path_boost

score_depth1 = compute_path_boost("https://example.com/articles")
score_depth2 = compute_path_boost("https://example.com/articles/diet")

# depth 1: decay^0 = 1.0; depth 2: decay^1 = 0.8
# So score_depth1 should be higher than score_depth2 (ceteris paribus)
assert score_depth1 > score_depth2
print(f"✅ AC-3: depth1={score_depth1:.4f} > depth2={score_depth2:.4f}")
```

---

### Scenario 4: XNG Returns 0 Results (AC-4)

```python
import asyncio
from unittest.mock import AsyncMock, patch
from src.tools.web import web_search

async def test_no_results():
    with patch("src.tools.web.search.xng_search.search_xng", return_value=[]):
        result = await web_search("asdfghjklqwerty12345")
        assert result.found == False
        assert result.combined_text == ""
        assert result.top_urls == []
    print("✅ AC-4: 0 results → no ranking/scraping triggered")

asyncio.run(test_no_results())
```

---

### Scenario 5: One URL Scrape Fails (AC-5)

```python
import asyncio
from unittest.mock import AsyncMock, patch
from src.tools.web import web_search
from src.tools.web.scraper.crawl4ai_scraper import ScrapedContent

async def test_partial_scrape_failure():
    mock_contents = [
        ScrapedContent(url="https://url-a.com", markdown="Content A", success=True, error=None),
        ScrapedContent(url="https://url-b.com", markdown="", success=False, error="403 Forbidden"),
        ScrapedContent(url="https://url-c.com", markdown="Content C", success=True, error=None),
    ]
    with patch("src.tools.web.scraper.crawl4ai_scraper.scrape_urls", return_value=mock_contents):
        result = await web_search("tiểu đường")
        assert result.found == True
        assert "Content A" in result.combined_text
        assert "Content C" in result.combined_text
        successful = [c for c in result.scraped_contents if c.success]
        assert len(successful) == 2
    print("✅ AC-5: System survives 1 URL failure, returns 2 successful scrapes")

asyncio.run(test_partial_scrape_failure())
```

---

## Unit Test Run Commands

```bash
# Run all web tool unit tests
pytest tests/unit/tools/web/ -v

# Run only ranking tests (no network)
pytest tests/unit/tools/web/test_scorer.py -v

# Run integration tests (requires SearXNG Docker)
pytest tests/integration/test_web_search_integration.py -v -m "integration"
```

**Expected results**:
- All unit tests pass without network access.
- Integration tests pass when SearXNG Docker is running.
- No exceptions raised for partial scrape failures.
