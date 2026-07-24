"""
BGE-M3 embedding model singleton for DiaCareFlow (UC-014).

Provides a module-level singleton that is loaded once at application startup
via FastAPI lifespan and reused across all RAG calls.

Usage:
    # Load at startup (called from main.py lifespan):
    load_bge_m3()

    # Use anywhere in the app:
    model = get_bge_m3()
    encoded = model.encode(texts, batch_size=12, max_length=8192)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_MODEL_NAME = "BAAI/bge-m3"
_bge_m3_instance = None  # module-level singleton


def load_bge_m3(max_retries: int = 3, retry_delay_seconds: float = 2.0) -> None:
    """
    Load the BGE-M3 model into memory as a module-level singleton.

    Retries up to `max_retries` times on failure. Should be called once
    during FastAPI lifespan startup before any requests are served.

    Raises:
        RuntimeError: if the model cannot be loaded after all retries.
    """
    global _bge_m3_instance

    if _bge_m3_instance is not None:
        logger.info("BGE-M3 model already loaded, skipping.")
        return

    from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415
    import torch

    # Force PyTorch to use float16 by default for all new tensors / models
    torch.set_default_dtype(torch.float16)
    
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Loading BGE-M3 embedding model (attempt %d/%d): %s",
                attempt,
                max_retries,
                _MODEL_NAME,
            )
            # Pass use_fp16=True explicitly just in case
            model = BGEM3FlagModel(_MODEL_NAME, use_fp16=True)
            _bge_m3_instance = model
            logger.info("BGE-M3 model loaded successfully in float16.")
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "BGE-M3 load attempt %d/%d failed: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                logger.info("Retrying in %.1f seconds…", retry_delay_seconds)
                time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Failed to load BGE-M3 model after {max_retries} attempts. "
        f"Please ensure the model weights are available (run: "
        f"`python -c \"from FlagEmbedding import BGEM3FlagModel; "
        f"BGEM3FlagModel('{_MODEL_NAME}')\"` to trigger a download). "
        f"Last error: {last_exc}"
    )


def get_bge_m3():
    """
    Return the cached BGE-M3 model instance.

    Raises:
        RuntimeError: if the model has not been loaded yet via `load_bge_m3()`.
    """
    if _bge_m3_instance is None:
        raise RuntimeError(
            "BGE-M3 model has not been initialised. "
            "Ensure `load_bge_m3()` is called during application startup."
        )
    return _bge_m3_instance
