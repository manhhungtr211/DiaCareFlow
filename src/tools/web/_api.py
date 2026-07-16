"""
Public API orchestrator for the UC-011 XNG Search & Web Scraper pipeline.

web_search(query) orchestrates:
  1. search_xng()     — fetch up to XNG_MAX_RESULTS candidate URLs
  2. rank_urls()      — composite score & sort; optionally call Jina reranker
  3. scrape_urls()    — parallel scrape of top-N URLs with Crawl4ai
  4. aggregate        — join successful markdown results into combined_text
  5. return WebSearchResponse
"""

from __future__ import annotations

import asyncio
import logging

from src.tools.web.models import RankingConfig, WebSearchResponse
from src.tools.web.ranking.jina_reranker import compute_jina_boost
from src.tools.web.ranking.scorer import rank_urls
from src.tools.web.scraper.crawl4ai_scraper import scrape_urls
from src.tools.web.search.xng_search import search_xng

# Config constants imported at module level so they can be patched in tests
from src.config import JINA_API_KEY, SCRAPE_TIMEOUT, XNG_MAX_RESULTS  # noqa: E402

logger = logging.getLogger(__name__)


async def web_search(query: str) -> WebSearchResponse:
    """
    Search the web for *query* and return top-3 scraped markdown content.

    Pipeline:
        1. Call XNG Search → up to XNG_MAX_RESULTS URLs  (SearchResult list)
        2. If empty → return WebSearchResponse(found=False)  [AC-4]
        3. Rank with composite scoring (hostname + path + freq + jina)
        4. Select top scrape_top_n (default 3) scored URLs
        5. Scrape those URLs in parallel with Crawl4ai  [AC-5]
        6. Aggregate successful markdown into combined_text
        7. Return WebSearchResponse(found=True)

    Args:
        query: The user's question or search keywords.

    Returns:
        WebSearchResponse — always returned; raises only SearchError on XNG failure.
    """
    logger.info("[web_search] query=%r", query)
    results = await search_xng(query, max_results=XNG_MAX_RESULTS)
    logger.info("[web_search] XNG returned %d results", len(results))

    # -----------------------------------------------------------------------
    # Step 2: AC-4 — empty results early return
    # -----------------------------------------------------------------------
    if not results:
        logger.info("[web_search] No results — returning found=False")
        return WebSearchResponse(
            query=query,
            result=[],
            scored_result=[],
            scraped_contents=[],
            combined_text="",
            found=False,
        )

    # -----------------------------------------------------------------------
    # Step 3: Jina reranking (optional, graceful degrade)
    # -----------------------------------------------------------------------
    config = RankingConfig()

    jina_key = JINA_API_KEY or None
    if jina_key:
        logger.info("[web_search] Computing Jina boosts for %d URLs", len(results))
        jina_boosts = await compute_jina_boost(
            query=query,
            results=results,
            api_key=jina_key,
            jina_weight=config.jina_weight,
        )
    else:
        jina_boosts = {}

    # -----------------------------------------------------------------------
    # Step 3 (cont.): Rank all results
    # -----------------------------------------------------------------------
    scored = rank_urls(results, config, jina_boosts=jina_boosts)
    logger.info(
        "[web_search] Ranked %d URLs; top URL: %s (score=%.3f)",
        len(scored),
        scored[0].url if scored else "N/A",
        scored[0].final_score if scored else 0.0,
    )

    # -----------------------------------------------------------------------
    # Step 4: Select top-N for scraping
    # -----------------------------------------------------------------------
    top_n = config.scrape_top_n
    top_scored = scored[:top_n]
    top_urls = [s.url for s in top_scored]
    logger.info("[web_search] Scraping top %d URLs: %s", len(top_urls), top_urls)

    # -----------------------------------------------------------------------
    # Step 5: Scrape in parallel (AC-5 — per-URL errors isolated)
    # -----------------------------------------------------------------------
    scraped = await scrape_urls(top_urls, timeout=SCRAPE_TIMEOUT)
    success_count = sum(1 for c in scraped if c.success)
    logger.info("[web_search] Scrape complete: %d/%d succeeded", success_count, len(scraped))

    # -----------------------------------------------------------------------
    # Step 6: Aggregate successful markdown
    # -----------------------------------------------------------------------
    combined_text = "\n\n".join(
        c.markdown for c in scraped if c.success and c.markdown
    )

    # -----------------------------------------------------------------------
    # Step 7: Return response
    # -----------------------------------------------------------------------
    return WebSearchResponse(
        query=query,
        result=results,
        scored_result=top_scored,
        scraped_contents=scraped,
        combined_text=combined_text,
        found=True,
    )
