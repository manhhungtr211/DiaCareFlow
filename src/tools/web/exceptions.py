"""
Custom exceptions for the UC-011 XNG Search & Web Scraper feature.
"""

from __future__ import annotations


class SearchError(Exception):
    """Raised when the SearXNG API is unreachable or returns an HTTP 5xx error."""


class ScrapeError(Exception):
    """
    Internal per-URL scraping failure.

    Caught inside scrape_urls() and converted to ScrapedContent(success=False).
    Never propagated to the caller of web_search() (AC-5).
    """
