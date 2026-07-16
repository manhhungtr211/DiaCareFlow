"""
Composite URL ranking algorithm — UC-011.

Per-URL scoring formula:
    hostname_boost  = host_freq * multiplier * config.host_name_weight
    path_boost      = sum(decay^i for i, seg in enumerate(path_segments))
                      * config.path_boost_weight
    freq_boost      = result.weight * config.freq_weight
    jina_rerank_boost = jina_score * config.jina_weight   (optional, 0.0 if unavailable)

    raw_total   = hostname_boost + path_boost + freq_boost + jina_rerank_boost
    final_score = clamp(raw_total, config.score_min, config.score_max)

AC-2: trusted domain → multiplier = config.trusted_multiplier (default 2.0)
AC-3: path depth 1 → decay^0 = 1.0; depth 2 → decay^1 = 0.8; depth 3 → decay^2 = 0.64
"""

from __future__ import annotations

import logging
from collections import Counter
from urllib.parse import urlparse

from src.tools.web.config import TrustedDomainRegistry
from src.tools.web.models import RankingConfig, ScoredURL, SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp *value* to the inclusive range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def _hostname(url: str) -> str:
    """Return the hostname of *url* in lower-case, or empty string on parse error."""
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _path_segments(url: str) -> list[str]:
    """Return non-empty path segments for *url* (excludes leading slash)."""
    try:
        path = urlparse(url).path or ""
        return [seg for seg in path.split("/") if seg]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# T012 — hostname boost
# ---------------------------------------------------------------------------


def compute_hostname_boost(
    url: str,
    config: RankingConfig,
    *,
    hostname_counts: dict[str, int] | None = None,
    total_urls: int,
) -> float:
    """
    Compute the hostname credibility boost for one URL.

    AC-2: trusted domain → multiplier = config.trusted_multiplier (2.0)
          non-trusted    → multiplier = 1.0

    host_freq = count_of_this_hostname / total_urls   (normalised [0, 1])
    boost = host_freq * multiplier * config.host_name_weight
    """
    registry = TrustedDomainRegistry()
    print(f"url: {url}")
    host = _hostname(url)
    print(f"host: {host}")
    
    count = (hostname_counts or {}).get(host, 1)
    print(f"count: {count}")
    host_freq = count / max(total_urls, 1)
    print(f"host_freq: {host_freq}")
    print(f"total_urls: {total_urls}")
    multiplier = config.trusted_multiplier if registry.is_trusted(host) else 1.0
    print(f"multiplier: {multiplier}")
    return host_freq * multiplier * config.host_name_weight


# ---------------------------------------------------------------------------
# T013 — path boost
# ---------------------------------------------------------------------------


def compute_path_boost(url: str, config: RankingConfig | None = None) -> float:
    """
    Compute the path-depth decay boost for one URL.

    AC-3: depth-1 segment contributes decay^0 = 1.0
          depth-2 segment contributes decay^1 = 0.8
          depth-3 segment contributes decay^2 = 0.64  …

    boost = sum(decay^i for i in range(len(segments))) * config.path_boost_weight
    """
    if config is None:
        config = RankingConfig()

    segments = _path_segments(url)
    if not segments:
        return 0.0

    raw = sum(config.decay_factor ** i for i in range(len(segments)))
    return raw * config.path_boost_weight


# ---------------------------------------------------------------------------
# T014 — frequency boost
# ---------------------------------------------------------------------------


def compute_freq_boost(weight: float, config: RankingConfig) -> float:
    """
    Compute the frequency boost from a SearchResult.weight value.

    boost = weight * config.freq_weight
    """
    return weight * config.freq_weight


# ---------------------------------------------------------------------------
# T015 — rank_urls (depends on T012–T014)
# ---------------------------------------------------------------------------


def rank_urls(
    results: list[SearchResult],
    config: RankingConfig | None = None,
    *,
    jina_boosts: dict[str, float] | None = None,
) -> list[ScoredURL]:
    """
    Score and sort a list of SearchResult objects.

    Args:
        results:     Raw results from XNG Search.
        config:      Ranking config; uses defaults if None.
        jina_boosts: Pre-computed per-URL Jina boost scores.
                     If None, jina_rerank_boost defaults to 0.0.

    Returns:
        List of ScoredURL sorted descending by final_score.
    """
    if config is None:
        config = RankingConfig()

    if not results:
        return []

    # Pre-compute hostname frequencies across all results
    hostnames = [_hostname(r.url) for r in results]
    hostname_counts = dict(Counter(hostnames))
    total = len(results)

    scored: list[ScoredURL] = []
    for result in results:
        h_boost = compute_hostname_boost(
            result.url,
            config,
            hostname_counts=hostname_counts,
            total_urls=total,
        )
        p_boost = compute_path_boost(result.url, config)
        f_boost = compute_freq_boost(result.weight, config)
        j_boost = (jina_boosts or {}).get(result.url, 0.0)

        raw = h_boost + p_boost + f_boost + j_boost
        final = _clamp(raw, config.score_min, config.score_max)

        scored.append(
            ScoredURL(
                **result.model_dump(),
                hostname_boost=h_boost,
                path_boost=p_boost,
                freq_boost=f_boost,
                jina_rerank_boost=j_boost,
                final_score=final,
            )
        )
        logger.debug(
            "Scored %s → hostname=%.3f path=%.3f freq=%.3f jina=%.3f final=%.3f",
            result.url,
            h_boost,
            p_boost,
            f_boost,
            j_boost,
            final,
        )

    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored
