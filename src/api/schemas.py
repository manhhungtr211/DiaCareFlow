"""
Pydantic schemas for the FastAPI REST API layer.

Defines request/response models used by the API endpoints.
These are separate from core domain models (src/rag/qa/data_models.py)
to keep the API layer independent of pipeline internals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Validates incoming POST requests to /api/chat."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question. Must not be empty and must be <= 2000 characters.",
    )


class SourceItem(BaseModel):
    """Represents a single document source used for generating the answer."""

    source: str = Field(..., description="The name/path of the source document.")
    score: float = Field(..., description="The retrieval relevance score.")


class ChatResponse(BaseModel):
    """Standardized JSON response returned to the client from /api/chat."""

    text: str = Field(
        ..., description="The generated answer or a fallback string."
    )
    is_refused: bool = Field(
        default=False,
        description="True if the question was blocked by guardrails or refused by the LLM.",
    )
    refuse_reason: str | None = Field(
        default=None,
        description="The reason for refusal, if is_refused is true.",
    )
    sources: list[SourceItem] = Field(
        default_factory=list,
        description="List of sources used. Empty if refused.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description='Additional information, e.g., {"processing_time_ms": 1200}.',
    )


class HealthResponse(BaseModel):
    """Response for the /api/health endpoint."""

    status: str = Field(
        ..., description='System status: "ok" or "degraded".'
    )
    qdrant: str = Field(
        ..., description='Qdrant connection status: "connected" or "disconnected".'
    )
    version: str = Field(
        default="1.0.0", description="API version."
    ) 
