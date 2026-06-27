"""
Supervisor Agent node for the LangGraph pipeline.

Receives the question after Harm Assessment, initializes tracking metadata,
and routes to RAG Agent. Acts as the central coordination point.
"""
#node này hiện chưa có chức năng gì
from __future__ import annotations

import logging
from typing import Any

from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def supervisor_node(state: AgentState) -> dict[str, Any]:
    """
    Supervisor Agent — receives question after harm assessment passes.

    Reads: user_input, is_safe
    Writes: nodes_visited, error
    """
    logger.info("Supervisor Agent: processing question")

    try:
        user_input = state.get("user_input", "")

        # Input validation (edge cases)
        if not user_input or not user_input.strip():
            logger.warning("Supervisor: received empty input")
            return {
                "nodes_visited": ["supervisor"],
                "error": "Câu hỏi không hợp lệ. Vui lòng nhập câu hỏi rõ ràng.",
            }

        if not any(c.isalnum() for c in user_input):
            logger.warning("Supervisor: received special-char-only input")
            return {
                "nodes_visited": ["supervisor"],
                "error": "Vui lòng nhập câu hỏi rõ ràng bằng văn bản.",
            }

        # Question has already been validated by Harm Assessment
        # Supervisor logs and routes forward to RAG Agent
        logger.info(
            f"Supervisor: routing safe question to RAG Agent "
            f"(length={len(user_input)} chars)"
        )

        return {
            "nodes_visited": ["supervisor"],
        }

    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}", exc_info=True)
        return {
            "nodes_visited": ["supervisor"],
            "error": f"Supervisor error: {str(e)}",
        }
