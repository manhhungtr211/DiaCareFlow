# src/tools/web/config/__init__.py
"""
TrustedDomainRegistry singleton — loads trusted_domains.yaml once,
exposes is_trusted(hostname: str) -> bool.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_YAML_PATH = Path(__file__).parent / "trusted_domains.yaml"


class TrustedDomainRegistry:
    """Singleton that loads the trusted domains list from YAML on first access."""

    _instance: "TrustedDomainRegistry | None" = None
    _domains: frozenset[str]

    def __new__(cls) -> "TrustedDomainRegistry":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._domains = cls._load_domains()
            cls._instance = instance
        return cls._instance

    @staticmethod
    def _load_domains() -> frozenset[str]:
        try:
            with open(_YAML_PATH, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            domains = data.get("trusted_domains", [])
            logger.debug("Loaded %d trusted domains from %s", len(domains), _YAML_PATH)
            return frozenset(d.lower().strip() for d in domains)
        except FileNotFoundError:
            logger.warning("trusted_domains.yaml not found at %s — no domains trusted", _YAML_PATH)
            return frozenset()
        except Exception as exc:
            logger.error("Failed to load trusted domains: %s", exc)
            return frozenset()

    def is_trusted(self, hostname: str) -> bool:
        """Return True if *hostname* (or any parent domain) is in the trusted list."""
        hostname = hostname.lower().strip()
        if hostname in self._domains:
            return True
        # Also check parent domains (e.g. pubmed.ncbi.nlm.nih.gov → ncbi.nlm.nih.gov)
        parts = hostname.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self._domains:
                return True
        return False

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
