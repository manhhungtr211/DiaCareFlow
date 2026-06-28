"""
API route handlers for DiaCareFlow.

Defines the /api/chat and /api/health endpoints.
"""

from __future__ import annotations

import logging
import time
from qdrant_client import QdrantClient
from src.config import QDRANT_URL
from fastapi import APIRouter
from src.agents.pipeline import ask_langgraph
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SourceItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/chat", response_model=str)
async def chat(request: ChatRequest):
    """
    Process a user question through the Multi-Agent LangGraph pipeline.

    Accepts a validated ChatRequest, invokes the pipeline, and returns
    a ChatResponse with the answer, sources, refusal info, and metadata.
    """
    start_time = time.time()

    # Invoke the LangGraph pipeline (synchronous call)
    answer = ask_langgraph(request.question)

    elapsed_ms = round((time.time() - start_time) * 1000)

    # Map pipeline Answer → API ChatResponse
    sources = [
        SourceItem(source=chunk.source, score=chunk.score)
        for chunk in answer.sources
    ]
    return answer.text
"""
    return ChatResponse(
        text=answer.text,
        is_refused=answer.is_refused,
        refuse_reason=answer.refuse_reason,
        sources=sources,
        metadata={"processing_time_ms": elapsed_ms},
    )
"""
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Reports system status and Qdrant connectivity.
    Returns status "ok" when all services are reachable,
    or "degraded" when Qdrant is unavailable (E4).
    """
    qdrant_status = _check_qdrant()
    system_status = "ok" if qdrant_status == "connected" else "degraded"

    return HealthResponse(
        status=system_status,
        qdrant=qdrant_status,
        version="1.0.0",
    )


def _check_qdrant() -> str:
    """
    Check Qdrant server connectivity.

    Returns "connected" if the Qdrant server responds,
    "disconnected" otherwise.
    """
    try:
        client = QdrantClient(url=QDRANT_URL, timeout=3)
        # A simple collections list call to verify connectivity
        client.get_collections()
        return "connected"
    except Exception as exc:
        logger.warning("Qdrant health check failed: %s", exc)
        return "disconnected"
