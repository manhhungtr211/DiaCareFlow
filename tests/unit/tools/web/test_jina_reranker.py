"""
Unit tests for src/tools/web/ranking/jina_reranker.py (T019).

All HTTP calls are mocked — no network access required.
"""

from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.web.ranking.jina_reranker import compute_jina_boost
from src.tools.web.models import SearchResult


def _make_results(n: int = 2) -> list[SearchResult]:
    return [
        SearchResult(
            url=f"https://url-{i}.com",
            title=f"Title {i}",
            content=f"Content {i}",
            weight=0.8,
            engine="test"
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Graceful degrade when api_key is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_jina_boost_no_api_key_returns_empty():
    """When api_key is None, compute_jina_boost must return {} without any HTTP call."""
    boosts = await compute_jina_boost("query", _make_results(), api_key=None)
    assert boosts == {}


@pytest.mark.asyncio
async def test_compute_jina_boost_empty_api_key_returns_empty():
    """When api_key is empty string, compute_jina_boost must return {}."""
    boosts = await compute_jina_boost("query", _make_results(), api_key="")
    assert boosts == {}


@pytest.mark.asyncio
async def test_compute_jina_boost_empty_results_returns_empty():
    """When results is empty, compute_jina_boost must return {}."""
    boosts = await compute_jina_boost("query", [], api_key="fake-key")
    assert boosts == {}


# ---------------------------------------------------------------------------
# Happy path — score parse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_jina_boost_parses_score():
    """When Jina API returns results array, compute_jina_boost should return dict mapping url to score * jina_weight."""
    results = _make_results(2)
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {"index": 0, "relevance_score": 0.8},
            {"index": 1, "relevance_score": 0.6}
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        boosts = await compute_jina_boost(
            "test query",
            results,
            api_key="fake-key",
            jina_weight=0.1,
        )

    assert len(boosts) == 2
    assert boosts["https://url-0.com"] == pytest.approx(0.08)  # 0.8 * 0.1
    assert boosts["https://url-1.com"] == pytest.approx(0.06)  # 0.6 * 0.1


# ---------------------------------------------------------------------------
# Exception handling — must NOT raise, returns {}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_jina_boost_http_error_returns_empty():
    """HTTP error must be caught; compute_jina_boost returns {} without raising."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("403", request=MagicMock(), response=MagicMock())
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        boosts = await compute_jina_boost("query", _make_results(), api_key="fake-key")

    assert boosts == {}


@pytest.mark.asyncio
async def test_compute_jina_boost_connection_error_returns_empty():
    """Connection errors must be caught; returns {} without raising."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client_cls.return_value = mock_client

        boosts = await compute_jina_boost("query", _make_results(), api_key="fake-key")

    assert boosts == {}


@pytest.mark.asyncio
async def test_compute_jina_boost_generic_exception_returns_empty():
    """Any unexpected exception must be caught; returns {}."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=RuntimeError("Unexpected"))
        mock_client_cls.return_value = mock_client

        boosts = await compute_jina_boost("query", _make_results(), api_key="fake-key")

    assert boosts == {}
