"""
Pydantic data models for the UC-011 XNG Search & Web Scraper feature.

All entities use pydantic.BaseModel for automatic validation and JSON serialisation.
SearchQuery is a @dataclass (pure input schema, no validation needed).
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. SearchQuery — input parameters for XNG Search API
# ---------------------------------------------------------------------------

@dataclass
class SearchQuery:
    """Parameters forwarded to the SearXNG search API."""

    query: str
    language: str | None = None
    pagenum: int | None = None
    time_range: str | None = None   # "day" | "week" | "month" | "year"
    safe_search: int | None = None  # 0 = off, 1 = moderate, 2 = strict


# ---------------------------------------------------------------------------
# Pydantic imports (deferred to keep dataclass definition above clean)
# ---------------------------------------------------------------------------

from pydantic import BaseModel, field_validator  # noqa: E402


# ---------------------------------------------------------------------------
# 2. SearchResult — a single result returned by XNG Search API
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """One result entry from the SearXNG /search?format=json endpoint."""

    url: str
    title: str
    content: str
    weight: float                       # XNG item.score, clamped to [0, 1]
    publishedDate: str | None = None    # ISO-8601 string or None
    engine: str = ""                    # Source search engine name

    @field_validator("weight")
    @classmethod
    def clamp_weight(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


# ---------------------------------------------------------------------------
# 3. ScoredURL — SearchResult enriched with per-component scoring data
# ---------------------------------------------------------------------------

class ScoredURL(SearchResult):
    """URL with composite ranking scores appended by the Ranker/Scorer."""

    freq_boost: float = 0.0            # From item.weight × freq_weight
    hostname_boost: float = 0.0        # Trusted domain check × multiplier
    path_boost: float = 0.0            # URL path depth decay
    jina_rerank_boost: float = 0.0     # Jina AI score (0.0 if API unavailable)
    final_score: float = 0.0           # clamp(sum of boosts, 0.0, 5.0)


# ---------------------------------------------------------------------------
# 4. ScrapedContent — result of a single Crawl4ai scrape attempt
# ---------------------------------------------------------------------------

class ScrapedContent(BaseModel):
    """Content scraped from one URL by Crawl4ai (AC-5 isolates per-URL errors)."""

    url: str
    markdown: str = ""
    success: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# 5. WebSearchResponse — final aggregated response returned to caller
# ---------------------------------------------------------------------------

class WebSearchResponse(BaseModel):
    """Aggregated response from the full web_search() pipeline."""

    query: str
    result: list[SearchResult] = []
    scored_result: list[ScoredURL] = []
    scraped_contents: list[ScrapedContent] = []
    combined_text: str = ""
    found: bool = True
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# 6. RankingConfig — tunable parameters for the ranking algorithm
# ---------------------------------------------------------------------------

class RankingConfig(BaseModel):
    """Configuration for the composite URL ranking algorithm."""

    host_name_weight: float = 0.4
    path_boost_weight: float = 0.2
    freq_weight: float = 0.3
    jina_weight: float = 0.1
    trusted_multiplier: float = 2.0   # AC-2: multiplier for trusted domains
    decay_factor: float = 0.8         # AC-3: decay per URL path depth level
    top_k: int = 5                    # Max URLs to fetch from XNG
    scrape_top_n: int = 3             # Top-N URLs to scrape after ranking
    score_min: float = 0.0
    score_max: float = 5.0
