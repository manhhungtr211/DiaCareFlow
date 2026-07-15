# Function Contract: `web_search(query)` — UC-011

**Module**: `src/tools/web/`  
**Type**: Standalone Python tool (not yet integrated into Agent graph per spec Notes)  
**Date**: 2026-07-15

---

## Public Interface

### `web_search(query: str) -> WebSearchResponse`

```python
async def web_search(query: str) -> WebSearchResponse:
    """
    Search the web for a query and return top-3 scraped content.

    Pipeline:
        1. Call XNG Search → up to 5 URLs
        2. Rank URLs using composite scoring (host_name + path_boost + freq + jina)
        3. Scrape top-3 URLs with Crawl4ai (parallel)
        4. Return aggregated content

    Args:
        query: The user's question or search keywords (non-empty string).

    Returns:
        WebSearchResponse with:
            - found=False + empty content if XNG returns 0 results
            - found=True + scraped content otherwise (partial OK if some URLs fail)

    Raises:
        SearchError: If XNG Search API is unreachable or returns HTTP 5xx.
    """
```

**Behavior Contracts**:
- **[CONTRACT-1]** If XNG returns 0 results → `found=False`, no ranking/scraping called.
- **[CONTRACT-2]** If XNG returns results → take top min(5, len(results)) URLs.
- **[CONTRACT-3]** Rank all URLs, select top 3 by `final_score` (descending).
- **[CONTRACT-4]** Scrape top-3 in parallel; per-URL failures are isolated (logged, not raised).
- **[CONTRACT-5]** Score normalization: clamp raw total to [0, 5].
- **[CONTRACT-6]** If all 3 scrapes fail → return `WebSearchResponse` with empty `combined_text`.

---

## Sub-function Contracts

### `search_xng(query: str, max_results: int = 5) -> list[SearchResult]`

```python
async def search_xng(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Call XNG Search API and parse top results.

    Raises:
        SearchError: On connection failure or HTTP 5xx.
    Returns:
        List of SearchResult (may be empty if no results found).
    """
```

### `rank_urls(results: list[SearchResult], config: RankingConfig) -> list[ScoredURL]`

```python
def rank_urls(
    results: list[SearchResult],
    config: RankingConfig | None = None
) -> list[ScoredURL]:
    """
    Score and sort URLs. Returns sorted list (descending by final_score).

    Formula per URL:
        host_score  = host_freq * multiplier * config.host_name_weight
        path_score  = sum(prefix_freq * decay^(depth-1)) * config.path_boost_weight
        freq_score  = result.weight * config.freq_weight
        jina_score  = jina_rating * config.jina_weight
        raw_total   = host_score + path_score + freq_score + jina_score
        final_score = clamp(raw_total, config.score_min, config.score_max)

    AC-2: trusted domain → multiplier = config.trusted_multiplier (2.0)
    AC-3: depth 1 → decay^0 = 1.0; depth 2 → decay^1 = 0.8
    """
```

### `scrape_urls(urls: list[str], timeout: int) -> list[ScrapedContent]`

```python
async def scrape_urls(urls: list[str], timeout: int = 10) -> list[ScrapedContent]:
    """
    Scrape multiple URLs in parallel using Crawl4ai.

    Per-URL errors are caught and returned as ScrapedContent(success=False).
    AC-5: one URL failing does not prevent others from being returned.
    """
```

---

## Error Types

```python
class SearchError(Exception):
    """Raised when XNG Search API is unavailable or returns server error."""
    pass

class ScrapeError(Exception):
    """Internal per-URL scraping failure (caught inside scrape_urls, not raised)."""
    pass
```

---

## Caller Expectations

| Scenario | `found` | `combined_text` | `error` |
|----------|---------|----------------|---------|
| Happy path (3 URLs scraped) | True | Non-empty markdown | None |
| XNG 0 results | False | "" | None |
| XNG API error | raises `SearchError` | — | — |
| 1/3 URL scrape fails | True | From 2 URLs | None |
| All 3 URLs scrape fail | True | "" | None |
