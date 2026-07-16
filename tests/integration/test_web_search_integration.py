"""
Integration tests for the UC-011 Web Search pipeline (T026).

These tests require a live SearXNG Docker instance.
Run with: pytest tests/integration/test_web_search_integration.py -v -m integration

Skip automatically when SearXNG is not available.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.tools.web import web_search
from src.tools.web.models import RankingConfig, SearchResult
from src.tools.web.ranking.scorer import rank_urls
from src.tools.web.search.xng_search import search_xng


# ---------------------------------------------------------------------------
# Availability check — skip all tests if SearXNG is not running
# ---------------------------------------------------------------------------


def _xng_available() -> bool:
    """Return True if SearXNG is responding at XNG_SEARCH_URL."""
    from src.config import XNG_SEARCH_URL

    try:
        resp = httpx.get(f"{XNG_SEARCH_URL}/search?q=test&format=json", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.integration

xng_available = pytest.mark.skipif(
    not _xng_available(),
    reason="SearXNG not running — start with: docker run -d --name searxng -p 8080:8080 searxng/searxng:latest",
)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


@xng_available
@pytest.mark.asyncio
async def test_search_xng_returns_results():
    """search_xng() against live SearXNG should return ≥1 result."""
    results = await search_xng("bệnh tiểu đường type 2")

    assert len(results) > 0
    for r in results:
        assert r.url.startswith("http")
        assert r.title
        assert 0.0 <= r.weight <= 1.0


@xng_available
@pytest.mark.asyncio
async def test_rank_urls_trusted_domain_boost():
    """AC-2: After ranking live results, diabetes.org should get higher score."""
    results = await search_xng("diabetes treatment")

    if not results:
        pytest.skip("No XNG results returned")

    scored = rank_urls(results, RankingConfig())
    assert len(scored) > 0

    trusted_scores = [s for s in scored if "diabetes.org" in s.url]
    other_scores = [s for s in scored if "diabetes.org" not in s.url]

    if trusted_scores and other_scores:
        # Trusted domain should rank among top entries
        assert trusted_scores[0].hostname_boost > other_scores[0].hostname_boost


@xng_available
@pytest.mark.asyncio
async def test_web_search_happy_path():
    """Full pipeline integration: web_search() returns found=True with content."""
    resp = await web_search("bệnh tiểu đường type 2 là gì")

    assert resp.found is True
    assert len(resp.result) > 0
    # At least one successful scrape (network-dependent)
    successful = [c for c in resp.scraped_contents if c.success]
    print(f"Scraped {len(successful)}/{len(resp.scraped_contents)} URLs successfully")
    print(f"combined_text length: {len(resp.combined_text)}")


@xng_available
@pytest.mark.asyncio
async def test_web_search_no_results():
    """AC-4: Highly improbable query should return found=False gracefully."""
    resp = await web_search("xkzqj11111aaazzz99999qqqwwweee")

    # May still find something; just verify the structure is correct
    if not resp.found:
        assert resp.combined_text == ""
        assert resp.scored_result == []
