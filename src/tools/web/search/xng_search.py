"""
XNG Search API async client — UC-011.

Calls the SearXNG /search?format=json endpoint and parses results into
a list of SearchResult Pydantic models.
"""

from __future__ import annotations

import logging

import httpx

from src.tools.web.exceptions import SearchError
from src.tools.web.models import SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search_xng(
    query: str,
    max_results: int = 5,
    *,
    base_url: str | None = None,
) -> list[SearchResult]:
    """
    Call SearXNG and return up to *max_results* parsed SearchResult objects.

    Args:
        query:       The search query string.
        max_results: Maximum number of results to request from SearXNG.
        base_url:    Override for the SearXNG base URL (defaults to
                     XNG_SEARCH_URL from config).

    Returns:
        A list of SearchResult objects.  Empty list if SearXNG returns 0 hits.

    Raises:
        SearchError: On connection failure or HTTP 5xx response.
    """
    from src.config import XNG_SEARCH_URL  # imported lazily to avoid circular deps at module load

    url_base = base_url or XNG_SEARCH_URL
    endpoint = f"{url_base.rstrip('/')}/search"
    params = {
        "q": query,
        "format": "json",
        "results": max_results,
    }

    logger.info("XNG search: query=%r max_results=%d url=%s", query, max_results, url_base)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint, params=params)
    except httpx.RequestError as exc:
        raise SearchError(f"XNG Search connection error: {exc}") from exc

    if response.status_code >= 500:
        raise SearchError(
            f"XNG Search returned HTTP {response.status_code}: {response.text[:200]}"
        )

    # Non-5xx non-200 codes (e.g. 400) — log and return empty
    if response.status_code != 200:
        logger.warning("XNG Search returned HTTP %d — treating as no results", response.status_code)
        return []

    data = response.json()
    raw_results: list[dict] = data.get("results", [])

    if not raw_results:
        logger.info("XNG Search returned 0 results for query=%r", query)
        return []

    results: list[SearchResult] = []
    for item in raw_results[:max_results]:
        # SearXNG uses "score" field for the relevance weight
        try:
            result = SearchResult(
                url=item.get("url", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                weight=float(item.get("score", 0.0)),
                publishedDate=item.get("publishedDate"),
                engine=item.get("engine", ""),
            )
            results.append(result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping malformed XNG result: %s — %s", item.get("url"), exc)

    logger.info("XNG search: got %d results", len(results))
    return results


# from src.config import JINA_API_KEY
# from src.tools.web.ranking.jina_reranker import compute_jina_boost
# from src.tools.web.ranking.scorer import rank_urls
# from src.tools.web.ranking.scorer import compute_hostname_boost
# from src.tools.web.ranking.scorer import _hostname
# from src.tools.web.models import RankingConfig
# from collections import Counter
# async def main():
#     query = "bệnh tiểu đường nhathuoclongchau"
#     results = await search_xng(query)
#     config = RankingConfig()
#     #final = await compute_jina_boost(query, result, api_key=JINA_API_KEY)
#     #rank_url = rank_urls(result, jina_boosts=final)
#     #print(rank_url)

#     hostnames = [_hostname(r.url) for r in results]
#     hostname_counts = dict(Counter(hostnames))
#     for result in results:
#         score = compute_hostname_boost(result.url, config, hostname_counts=hostname_counts)
#         print("url: ", result.url)
#         print("score: ", score)
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())