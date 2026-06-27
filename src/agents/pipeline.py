"""
Entry point for the LangGraph Multi-Agent pipeline.

Provides ask_langgraph() which is backward-compatible with the existing
ask() interface — returns the same Answer dataclass.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from src.agents.graph import compile_graph
from src.agents.state import AgentState, SafetyCategory
from src.rag.qa.data_models import Answer, ChunkResult

logger = logging.getLogger(__name__)

# Compile graph once at module level for reuse
_compiled_graph = None


def _get_graph():
    """Lazy-compile the graph on first use."""
    global _compiled_graph
    if _compiled_graph is None:
        logger.info("Compiling LangGraph pipeline (first invocation)")
        _compiled_graph = compile_graph()
    return _compiled_graph


def ask_langgraph(question: str, top_k: int = 3) -> Answer:
    """
    Entry point for the LangGraph Multi-Agent pipeline.

    Invokes the compiled StateGraph with the question, then converts
    the final AgentState into an Answer dataclass for backward compatibility.

    Args:
        question: The user's question text.
        top_k: Number of chunks to retrieve (passed through to RAG Agent).

    Returns:
        Answer dataclass compatible with the existing pipeline interface.
    """
    logger.info(f"ask_langgraph: received question (length={len(question)})")

    start_time = time.time()

    try:
        graph = _get_graph()

        # Build initial state
        initial_state: dict = {
            "user_input": question,
            "messages": [],
            "is_safe": True,
            "harm_task": SafetyCategory.SAFE,
            "rag_context": [],
            "suggestion_context": {},
            "messageId": "",
            "nodes_visited": [],
            "error": None,
        }

        # Invoke the graph
        final_state = graph.invoke(initial_state)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"ask_langgraph: completed in {elapsed_ms:.0f}ms, "
            f"nodes_visited={final_state.get('nodes_visited', [])}"
        )

        # Convert final state to Answer
        return _state_to_answer(final_state)

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"ask_langgraph: pipeline error after {elapsed_ms:.0f}ms: {e}",
            exc_info=True,
        )
        return Answer(
            text="Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
            sources=[],
            is_refused=False,
        )


def _state_to_answer(state: dict) -> Answer:
    """
    Convert final AgentState to Answer dataclass.

    Handles both the safe path (suggestion_context has final_answer)
    and the refusal path (suggestion_context has refusal_message).
    """
    is_safe = state.get("is_safe", True)
    suggestion = state.get("suggestion_context", {})
    error = state.get("error")

    # Error path — node encountered an error
    if error and not suggestion:
        return Answer(
            text=f"Đã xảy ra lỗi: {error}",
            sources=[],
            is_refused=False,
        )

    # Refusal path — question was unsafe
    if not is_safe:
        refusal_message = suggestion.get(
            "refusal_message",
            "Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi hỗ trợ.",
        )
        harm_task = state.get("harm_task", SafetyCategory.PRESCRIPTION)

        return Answer(
            text=refusal_message,
            sources=[],
            is_refused=True,
            refuse_reason=harm_task.value if isinstance(harm_task, SafetyCategory) else str(harm_task),
        )

    # Happy path — answer generated
    final_answer = suggestion.get("final_answer", "")
    sources_dicts = suggestion.get("sources", [])

    # Reconstruct ChunkResult objects for Answer
    sources = [
        ChunkResult(
            content=s.get("content", ""),
            source=s.get("source", "Unknown"),
            score=s.get("score", 0.0),
        )
        for s in sources_dicts
    ]

    return Answer(
        text=final_answer,
        sources=sources,
        is_refused=suggestion.get("is_refused", False),
        refuse_reason=suggestion.get("refuse_reason"),
    )
