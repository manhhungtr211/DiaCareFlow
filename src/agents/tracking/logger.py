"""
JSON tracking logger for LangGraph pipeline events.

Provides a singleton logger that writes each LogEvent as a single JSON line
to both stdout (via Python logging) and the append-only file logs/tracking.jsonl.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from src.agents.tracking.models import LogEvent

# ---------------------------------------------------------------------------
# Log file path — relative to project root, resolved at import time
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # src/agents/tracking → project root
_LOG_FILE = _PROJECT_ROOT / "logs" / "tracking.jsonl"


class _JsonLineFormatter(logging.Formatter):
    """Format a LogRecord whose 'msg' is already a dict into a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        if isinstance(record.msg, dict):
            return json.dumps(record.msg, ensure_ascii=False)
        return super().format(record)


def _build_logger() -> logging.Logger:
    """
    Build and configure the dedicated tracking logger.

    - StreamHandler → stdout JSON lines (visible in container logs / terminal)
    - FileHandler   → logs/tracking.jsonl (persistent append-mode file)
    """
    logger = logging.getLogger("diacareflow.tracking")

    # Avoid adding duplicate handlers if module is reimported (e.g. in tests)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't bubble up to root logger

    formatter = _JsonLineFormatter()

    # stdout handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File handler — ensure directory exists
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(_LOG_FILE), mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("tracking: could not open log file %s — %s", _LOG_FILE, exc)

    return logger


# Module-level singleton — initialised once on import
_tracking_logger = _build_logger()


class JsonTrackingLogger:
    """
    Thin wrapper around the dedicated tracking logger.

    Usage::

        from src.agents.tracking.logger import JsonTrackingLogger

     
        logger.emit(ev   logger = JsonTrackingLogger()ent)
    """

    def emit(self, event: LogEvent) -> None:
        """Serialise *event* and write it as a JSON line to all configured handlers."""
        try:
            _tracking_logger.info(event.to_dict())
        except Exception:
            # Never let logging errors crash the pipeline
            pass
