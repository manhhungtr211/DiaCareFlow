"""
Web scraping module using Crawl4ai (US4).
Handles parallel scraping with graceful error degradation per URL.
"""

from __future__ import annotations

import logging

from crawl4ai import AsyncWebCrawler

from src.tools.web.models import ScrapedContent

logger = logging.getLogger(__name__)


async def scrape_urls(urls: list[str], timeout: int = 10) -> list[ScrapedContent]:
    """
    Scrape multiple URLs in parallel using Crawl4ai.
    Returns a list of ScrapedContent in the same order as input URLs.
    Handles per-URL failures gracefully without crashing.
    """
    if not urls:
        return []

    logger.info("Scraping %d URLs...", len(urls))
    
    scraped_contents = []
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            results = await crawler.arun_many(urls=urls)
            
            for url, result in zip(urls, results):
                if result.success:
                    scraped_contents.append(
                        ScrapedContent(url=url, markdown=result.markdown, success=True)
                    )
                else:
                    error_msg = getattr(result, "error_message", "Unknown scrape error")
                    logger.warning("Failed to scrape %s: %s", url, error_msg)
                    scraped_contents.append(
                        ScrapedContent(url=url, markdown="", success=False, error=error_msg)
                    )
    except Exception as e:
        logger.warning("Crawler exception during arun_many: %s", e)
        for url in urls:
            scraped_contents.append(
                ScrapedContent(url=url, markdown="", success=False, error=str(e))
            )

    return scraped_contents
