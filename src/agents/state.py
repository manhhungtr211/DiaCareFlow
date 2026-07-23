"""
Shared state definitions for the LangGraph multi-agent pipeline.

AgentState is the TypedDict that flows through all nodes in the graph.
Each node reads from and writes to this shared state.

UC-012: Refactored to multi-agent parallel architecture.
  - Added: factor_results, suggestion_results, harm_sub_results, errors
    (all use Annotated[list, operator.add] for fan-in from parallel sub-agents)
  - Removed: rag_context (replaced by per-agent result fields)
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
    Shared state for the LangGraph multi-agent pipeline (UC-012).

    Extends MessagesState to get the built-in `messages` field with
    proper message accumulation. Additional fields track the pipeline's
    progress through triage, parallel sub-agents, and response generation.

    Fan-in fields (Annotated with operator.add):
        factor_results, suggestion_results, harm_sub_results, errors
        — Multiple parallel nodes append to these lists without overwriting.
    """

    # --- Input ---
    user_input: str  # Original question from the user

    # --- Triage Agent output (UC-012: renamed from harm_assessment) ---
    is_safe: bool  # Whether the question passed safety check
    harm_task: SafetyCategory  # Safety classification result

    # --- Supervisor output ---
    intent: str  # "SMALL_TALK" | "DIABETES" — set by supervisor_node
    follow_up_question: str
    should_response: bool
    small_talk_reply: str  # Pre-generated reply from supervisor LLM when intent == SMALL_TALK
    factor_question: str  # Sub-question for factor_agent
    suggestion_question: str  # Sub-question for suggestion_agent
    harm_question: str  # Sub-question for harm_agent


    # --- Sub-Agent results (UC-012: fan-in via operator.add reducer) ---
    factor_results: Annotated[list[dict], operator.add]
    # Written by: factor_agent_node
    # Format: [{"factor_summary": str, "sources": list[dict]}]

    suggestion_results: Annotated[list[dict], operator.add]
    # Written by: suggestion_agent_node
    # Format: [{"suggestion_summary": str, "sources": list[dict]}]

    harm_sub_results: Annotated[list[dict], operator.add]
    # Written by: harm_sub_agent_node
    # Format: [{"harm_summary": str}]

    # --- Error accumulation (UC-012: fan-in, per-node errors don't stop flow) ---
    errors: Annotated[list[str], operator.add]
    # Each node appends error strings; Response Agent surfaces them if needed.

    # --- Response output ---
    suggestion_context: dict  # Final answer and metadata from response agent

    # --- Metadata ---
    messageId: str  # Message identifier for tracking
    nodes_visited: Annotated[list[str], operator.add]  # Accumulate visited node names

    # --- Chat History (UC-009) ---
    chat_history: list  # Trimmed history for LLM prompt injection (populated by pipeline)
