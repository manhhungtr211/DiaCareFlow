"""
Jina AI Reranker integration — UC-011.

Computes `jina_rerank_boost` per URL using the Jina Reranker API.
Gracefully degrades to 0.0 when the API key is absent or any error occurs.
"""

from __future__ import annotations

import logging

import httpx

from src.tools.web.models import SearchResult

logger = logging.getLogger(__name__)

_JINA_BASE_URL = "https://api.jina.ai/v1/rerank"


async def compute_jina_boost(
    query: str,
    results: list[SearchResult],
    *,
    api_key: str | None,
    jina_weight: float = 0.1,
) -> dict[str, float]:
    """
    Fetch relevance scores from Jina Reranker API for a list of results.

    Args:
        query:       The search query.
        results:     List of SearchResult objects from XNG.
        api_key:     Jina API key. Pass ``None`` or ``""`` to skip (graceful degrade).
        jina_weight: Weight multiplier applied to the raw Jina score.

    Returns:
        Dict mapping URL to its boost (score * jina_weight).
        Returns empty dict on failure or missing API key.
    """
    if not api_key or not results:
        logger.debug("Jina API key not set or empty results — skipping reranking")
        return {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Combine title and content for Jina evaluation (as per T017)
    documents = [f"{r.title} {r.content}" for r in results]
    
    payload = {
        "model": "jina-reranker-v2-base-multilingual",
        "query": query,
        "documents": documents
    }

    try:
        import asyncio
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await asyncio.wait_for(
                client.post(_JINA_BASE_URL, headers=headers, json=payload),
                timeout=12.0
            )
        response.raise_for_status()
        data = response.json()
        
        boosts = {}
        for item in data.get("results", []):
            idx = item.get("index")
            relevance = float(item.get("relevance_score", 0.0))
            if idx is not None and 0 <= idx < len(results):
                url = results[idx].url
                boost = relevance * jina_weight
                boosts[url] = boost
                logger.debug("Jina score for %s: raw=%.3f boost=%.3f", url, relevance, boost)
        return boosts
    except Exception as exc:  # noqa: BLE001
        logger.warning("Jina reranker failed for query %r: %s — returning empty boosts", query, exc)
        return {}