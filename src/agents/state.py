"""
Shared state definitions for the LangGraph multi-agent pipeline.

AgentState is the TypedDict that flows through all nodes in the graph.
Each node reads from and writes to this shared state.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph import MessagesState


class SafetyCategory(str, Enum):
    """Classification of question safety level by Harm Assessment Agent."""

    SAFE = "SAFE"
    PRESCRIPTION = "PRESCRIPTION"
    DIAGNOSIS = "DIAGNOSIS"
    EMERGENCY = "EMERGENCY"


class AgentState(MessagesState):
    """
    Shared state for the LangGraph multi-agent pipeline.

    Extends MessagesState to get the built-in `messages` field with
    proper message accumulation. Additional fields track the pipeline's
    progress through harm assessment, RAG retrieval, and response generation.
    """

    # --- Input ---
    user_input: str  # Original question from the user

    # --- Harm Assessment output ---
    is_safe: bool  # Whether the question passed safety check
    harm_task: SafetyCategory  # Safety classification result

    # --- RAG output ---
    rag_context: list  # List of ChunkResult dicts from retriever

    # --- Response output ---
    suggestion_context: dict  # Final answer and metadata from response agent

    # --- Metadata ---
    messageId: str  # Message identifier for tracking
    nodes_visited: Annotated[list[str], operator.add]  # Accumulate visited node names (chưa biết cần dùng hay ko)
    error: Optional[str]  # Error message if any node fails
