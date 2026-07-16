"""
Unit tests for src/tools/web/_api.py — web_search() pipeline (T025).

All external I/O is mocked. Tests cover:
  - AC-1: Happy path — 3 URLs scraped, combined_text non-empty
  - AC-4: XNG returns [] → found=False, no rank/scrape called
  - AC-5: 1 scrape fails → found=True, combined_text from remaining 2
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.tools.web._api import web_search
from src.tools.web.models import ScrapedContent, SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_results(n: int = 3) -> list[SearchResult]:
    return [
        SearchResult(
            url=f"https://url-{i}.com/page",
            title=f"Title {i}",
            content=f"Content {i}",
            weight=0.8 - i * 0.1,
            engine="test",
        )
        for i in range(n)
    ]


def _make_scraped(urls: list[str], fail_index: int | None = None) -> list[ScrapedContent]:
    contents = []
    for i, url in enumerate(urls):
        if i == fail_index:
            contents.append(ScrapedContent(url=url, markdown="", success=False, error="403"))
        else:
            contents.append(ScrapedContent(url=url, markdown=f"Markdown from {url}", success=True))
    return contents


# ---------------------------------------------------------------------------
# AC-1: Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_happy_path_ac1():
    """AC-1: 3 URLs found, ranked, scraped → found=True, combined_text non-empty."""
    results = _make_results(3)
    urls = [r.url for r in results]
    scraped = _make_scraped(urls)

    with (
        patch("src.tools.web._api.search_xng", return_value=results),
        patch("src.tools.web._api.scrape_urls", return_value=scraped),
        patch("src.tools.web._api.JINA_API_KEY", None),
    ):
        resp = await web_search("bệnh tiểu đường")

    assert resp.found is True
    assert len(resp.result) == 3
    assert resp.combined_text != ""
    # All 3 successful markdowns joined
    for url in urls:
        assert f"Markdown from {url}" in resp.combined_text


# ---------------------------------------------------------------------------
# AC-4: XNG returns 0 results → found=False, no rank/scrape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_no_results_ac4():
    """AC-4: When XNG returns [], web_search must return found=False without ranking/scraping."""
    with (
        patch("src.tools.web._api.search_xng", return_value=[]) as mock_search,
        patch("src.tools.web._api.rank_urls") as mock_rank,
        patch("src.tools.web._api.scrape_urls") as mock_scrape,
    ):
        resp = await web_search("asdfghjklqwerty12345")

    assert resp.found is False
    assert resp.combined_text == ""
    assert resp.result == []
    assert resp.scored_result == []
    mock_rank.assert_not_called()
    mock_scrape.assert_not_called()


# ---------------------------------------------------------------------------
# AC-5: 1 of 3 scrapes fails → found=True, combined_text from 2 remaining
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_partial_scrape_failure_ac5():
    """AC-5: 1 scrape fails → system survives, found=True, combined from 2 URLs."""
    results = _make_results(3)
    urls = [r.url for r in results]
    scraped = _make_scraped(urls, fail_index=1)  # url-1 fails

    with (
        patch("src.tools.web._api.search_xng", return_value=results),
        patch("src.tools.web._api.scrape_urls", return_value=scraped),
        patch("src.tools.web._api.JINA_API_KEY", None),
    ):
        resp = await web_search("tiểu đường")

    assert resp.found is True
    successful = [c for c in resp.scraped_contents if c.success]
    assert len(successful) == 2
    assert f"Markdown from {urls[0]}" in resp.combined_text
    assert f"Markdown from {urls[2]}" in resp.combined_text
    # Failed URL content must NOT be in combined_text
    assert f"Markdown from {urls[1]}" not in resp.combined_text


# ---------------------------------------------------------------------------
# All scrapes fail → found=True but combined_text=""
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_all_scrapes_fail():
    """When all scrapes fail, combined_text is empty but found=True (results were found)."""
    results = _make_results(3)
    urls = [r.url for r in results]
    scraped = [
        ScrapedContent(url=url, markdown="", success=False, error="Blocked")
        for url in urls
    ]

    with (
        patch("src.tools.web._api.search_xng", return_value=results),
        patch("src.tools.web._api.scrape_urls", return_value=scraped),
        patch("src.tools.web._api.JINA_API_KEY", None),
    ):
        resp = await web_search("tiểu đường")

    assert resp.found is True
    assert resp.combined_text == ""
    assert len(resp.scraped_contents) == 3


# ---------------------------------------------------------------------------
# scored_result contains top-N scored URLs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_scored_result_top_n():
    """scored_result should contain at most scrape_top_n entries."""
    results = _make_results(5)  # 5 XNG results
    scraped = _make_scraped([r.url for r in results[:3]])

    with (
        patch("src.tools.web._api.search_xng", return_value=results),
        patch("src.tools.web._api.scrape_urls", return_value=scraped),
        patch("src.tools.web._api.JINA_API_KEY", None),
    ):
        resp = await web_search("test")

    assert len(resp.scored_result) <= 3  # default scrape_top_n = 3
