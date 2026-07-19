"""
Entry point for the LangGraph Multi-Agent pipeline.

Provides ask_langgraph() which is backward-compatible with the existing
ask() interface — returns the same Answer dataclass.

UC-009: Supports per-session chat history via MemorySaver checkpointer.
Pass a session_id to maintain conversation context across requests.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, trim_messages
from langchain_groq import ChatGroq

from src.agents.graph import compile_graph
from src.agents.state import AgentState, SafetyCategory
from src.config import CHAT_HISTORY_MAX_TOKENS, GENERATIVE_MODEL
from src.tools.rag.qa.data_models import Answer, ChunkResult

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


def _build_chat_history(messages: list) -> list:
    """
    Trim the accumulated messages to fit within the configured token limit.

    Uses langchain_core.messages.trim_messages with strategy='last'
    to keep the most recent turns and discard oldest ones.

    Args:
        messages: Full list of BaseMessage objects from MemorySaver state.

    Returns:
        Trimmed list of BaseMessage objects.
    """
    if not messages:
        return []

    original_count = len(messages)

    trimmed = trim_messages(
        messages,
        max_tokens=CHAT_HISTORY_MAX_TOKENS,
        strategy="last",
        token_counter=ChatGroq(model_name=GENERATIVE_MODEL),
        include_system=True,
        allow_partial=False,
    )

    trimmed_count = len(trimmed)
    logger.info(
        f"Chat history trimmed: original_count={original_count}, "
        f"trimmed_count={trimmed_count}, max_tokens={CHAT_HISTORY_MAX_TOKENS}"
    )

    return trimmed


def ask_langgraph(question: str, session_id: str | None = None) -> Answer:
    """
    Entry point for the LangGraph Multi-Agent pipeline.

    Invokes the compiled StateGraph with the question, then converts
    the final AgentState into an Answer dataclass for backward compatibility.

    Args:
        question: The user's question text.
        session_id: Optional session identifier for chat history.
                    Auto-generated UUID if None (no cross-request history).

    Returns:
        Answer dataclass compatible with the existing pipeline interface.
    # Auto-generate session_id for backward compat
    if session_id is None:
        session_id = str(uuid.uuid4())
"""    
    logger.info(
        f"ask_langgraph: received question (length={len(question)}), "
        f"session_id={session_id}"
    )

    start_time = time.time()

    try:
        graph = _get_graph()

        # UC-009: Build thread config for MemorySaver
        config = {"configurable": {"thread_id": session_id}}

        # UC-009: Get existing history from MemorySaver via graph state
        try:
            existing_state = graph.get_state(config)
            existing_messages = existing_state.values.get("messages", []) if existing_state.values else []
        except Exception:
            existing_messages = []

        # UC-009: Append current user message and trim history
        current_user_msg = HumanMessage(content=question, name="user")
        all_messages = list(existing_messages) + [current_user_msg]
        trimmed_history = _build_chat_history(all_messages)

        # Build initial state (UC-012: removed rag_context; added fan-in fields)
        initial_state: dict = {
            "user_input": question,
            "messages": [current_user_msg],
            "is_safe": True,
            "harm_task": SafetyCategory.SAFE,
            "intent": "DIABETES",
            "small_talk_reply": "",
            "factor_question": "",
            "suggestion_question": "",
            "harm_question": "",
            "factor_results": [],
            "suggestion_results": [],
            "harm_sub_results": [],
            "errors": [],
            "suggestion_context": {},
            "messageId": "",
            "nodes_visited": [],
            "chat_history": trimmed_history,
        }

        # Invoke the graph with thread config for MemorySaver
        final_state = graph.invoke(initial_state, config=config)

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"ask_langgraph: completed in {elapsed_ms:.0f}ms, "
            f"nodes_visited={final_state.get('nodes_visited', [])}"
        )

        # Convert final state to Answer
        answer = _state_to_answer(final_state)

        # UC-009 / T015: Only persist to history if the message was safe.
        # If triage_agent determined it's unsafe, don't add to history
        # so that unsafe messages don't pollute future context.
        is_safe = final_state.get("is_safe", True)
        if is_safe:
            ai_msg = AIMessage(content=answer.text, name="assistant")
            graph.update_state(config, {"messages": [ai_msg]})
        else:
            logger.info("ask_langgraph: unsafe message — skipping history persistence")

        return answer

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
    errors = state.get("errors", [])  # UC-012: errors is now a list (was singular 'error')

    # Error path — node encountered an error with no usable suggestion_context
    if errors and not suggestion:
        error_text = "; ".join(errors)
        return Answer(
            text=f"Đã xảy ra lỗi: {error_text}",
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
