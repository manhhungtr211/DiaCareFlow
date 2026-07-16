"""
Unit tests for src/tools/web/scraper/crawl4ai_scraper.py (T022).

AsyncWebCrawler is fully mocked — no actual browser/network access.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.web.scraper.crawl4ai_scraper import scrape_urls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_crawl_result(success: bool, markdown: str = "", error_message: str = "") -> MagicMock:
    r = MagicMock()
    r.success = success
    r.markdown = markdown
    r.error_message = error_message
    return r


def _patch_crawler(crawl_results: list[MagicMock]):
    """
    Patch crawl4ai.AsyncWebCrawler so that arun_many returns crawl_results.
    Returns the context manager patch.
    """
    mock_crawler_instance = AsyncMock()
    mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
    mock_crawler_instance.__aexit__ = AsyncMock(return_value=False)
    mock_crawler_instance.arun_many = AsyncMock(return_value=crawl_results)

    return patch("src.tools.web.scraper.crawl4ai_scraper.AsyncWebCrawler", return_value=mock_crawler_instance)


def _patch_crawler_exception(exc: Exception):
    mock_crawler_instance = AsyncMock()
    mock_crawler_instance.__aenter__ = AsyncMock(return_value=mock_crawler_instance)
    mock_crawler_instance.__aexit__ = AsyncMock(return_value=False)
    mock_crawler_instance.arun_many = AsyncMock(side_effect=exc)

    return patch("src.tools.web.scraper.crawl4ai_scraper.AsyncWebCrawler", return_value=mock_crawler_instance)


# ---------------------------------------------------------------------------
# scrape_urls — happy path (all succeed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_urls_all_succeed():
    """scrape_urls should return one ScrapedContent per URL in order."""
    urls = [
        "https://url-a.com",
        "https://url-b.com",
        "https://url-c.com",
    ]

    results = [
        _make_crawl_result(success=True, markdown=f"Content from {url}")
        for url in urls
    ]

    with _patch_crawler(results):
        scraped = await scrape_urls(urls)

    assert len(scraped) == 3
    assert all(r.success for r in scraped)
    assert scraped[0].url == "https://url-a.com"
    assert "url-b" in scraped[1].markdown


# ---------------------------------------------------------------------------
# AC-5: one URL reports failure → others still return
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_urls_one_fails_others_succeed():
    """AC-5: 1 URL failure must not prevent remaining URLs from being returned."""
    urls = [
        "https://url-a.com",
        "https://url-b.com",  # will fail
        "https://url-c.com",
    ]

    results = [
        _make_crawl_result(success=True, markdown="Content A"),
        _make_crawl_result(success=False, error_message="403 Forbidden"),
        _make_crawl_result(success=True, markdown="Content C"),
    ]

    with _patch_crawler(results):
        scraped = await scrape_urls(urls)

    assert len(scraped) == 3
    successful = [r for r in scraped if r.success]
    failed = [r for r in scraped if not r.success]

    assert len(successful) == 2
    assert len(failed) == 1
    assert failed[0].url == "https://url-b.com"
    assert "403 Forbidden" in failed[0].error

    # Order must be preserved
    assert scraped[0].url == "https://url-a.com"
    assert scraped[1].url == "https://url-b.com"
    assert scraped[2].url == "https://url-c.com"


# ---------------------------------------------------------------------------
# AC-5: exception handling (arun_many crashes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_urls_exception_returns_failure():
    """AC-5: Any exception in scrape_urls must return success=False for all URLs, never raise."""
    urls = ["https://example.com/page1", "https://example.com/page2"]

    with _patch_crawler_exception(RuntimeError("Browser crash")):
        scraped = await scrape_urls(urls)

    assert len(scraped) == 2
    assert all(not r.success for r in scraped)
    assert "Browser crash" in scraped[0].error
    assert scraped[0].url == urls[0]


# ---------------------------------------------------------------------------
# scrape_urls — empty input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_urls_empty_input():
    """scrape_urls([]) should return empty list."""
    results = await scrape_urls([])
    assert results == []
