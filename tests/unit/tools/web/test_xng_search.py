"""
Unit tests for src/tools/web/search/xng_search.py (T011).

All HTTP calls are mocked — no network access required.
"""

from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.web.search.xng_search import search_xng
from src.tools.web.exceptions import SearchError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_xng_response(results: list[dict], status_code: int = 200) -> MagicMock:
    """Build a mock httpx.Response for SearXNG."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"results": results}
    mock_resp.text = ""
    return mock_resp


SAMPLE_RESULTS = [
    {
        "url": "https://diabetes.org/article",
        "title": "Diabetes Overview",
        "content": "Comprehensive guide to diabetes management.",
        "score": 0.9,
        "engine": "google",
        "publishedDate": "2024-01-15",
    },
    {
        "url": "https://healthline.com/nutrition/diabetes-diet",
        "title": "Diabetes Diet Tips",
        "content": "Best foods for managing blood sugar.",
        "score": 0.7,
        "engine": "bing",
        "publishedDate": None,
    },
]


# ---------------------------------------------------------------------------
# Happy path — parses results correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_happy_path():
    """search_xng() should parse SearXNG JSON into SearchResult objects."""
    mock_resp = _make_xng_response(SAMPLE_RESULTS)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await search_xng("bệnh tiểu đường")

    assert len(results) == 2
    assert results[0].url == "https://diabetes.org/article"
    assert results[0].title == "Diabetes Overview"
    assert results[0].weight == pytest.approx(0.9)
    assert results[0].engine == "google"
    assert results[1].url == "https://healthline.com/nutrition/diabetes-diet"
    assert results[1].publishedDate is None


# ---------------------------------------------------------------------------
# AC-4: empty results list → return []
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_empty_results():
    """AC-4: When SearXNG returns 0 results, search_xng should return []."""
    mock_resp = _make_xng_response([])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await search_xng("zzz-no-results")

    assert results == []


# ---------------------------------------------------------------------------
# HTTP 500 → raise SearchError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_http_500_raises_search_error():
    """When SearXNG returns HTTP 5xx, search_xng should raise SearchError."""
    mock_resp = _make_xng_response([], status_code=500)
    mock_resp.text = "Internal Server Error"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(SearchError, match="HTTP 500"):
            await search_xng("query")


# ---------------------------------------------------------------------------
# Connection error → raise SearchError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_connection_error_raises_search_error():
    """When the HTTP client raises RequestError, search_xng should raise SearchError."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client_cls.return_value = mock_client

        with pytest.raises(SearchError, match="connection error"):
            await search_xng("query")


# ---------------------------------------------------------------------------
# weight clamping
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_weight_clamped():
    """Weight field should be clamped to [0, 1] by the model validator."""
    mock_resp = _make_xng_response([{
        "url": "https://example.com/page",
        "title": "Test",
        "content": "Content",
        "score": 2.5,   # out of range — should be clamped to 1.0
        "engine": "test",
    }])

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await search_xng("test")

    assert results[0].weight == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# max_results respected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_xng_max_results_respected():
    """search_xng should return at most max_results items."""
    many = [
        {"url": f"https://example.com/{i}", "title": f"T{i}", "content": "", "score": 0.5, "engine": "g"}
        for i in range(10)
    ]
    mock_resp = _make_xng_response(many)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        results = await search_xng("test", max_results=3)

    assert len(results) == 3
