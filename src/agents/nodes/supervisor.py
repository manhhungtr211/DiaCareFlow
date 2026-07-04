"""
Supervisor Agent node for the LangGraph pipeline.

Classifies user intent after Harm Assessment passes:
  - SMALL_TALK: greetings, thanks, casual chat → bypass RAG, reply inline
  - DIABETES: health/diabetes question → route to RAG Agent

Uses a single LLM call that both classifies AND generates the reply
for small-talk queries (to avoid a second LLM call in the response agent).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq

from src.agents.state import AgentState
from src.config import GENERATIVE_MODEL

logger = logging.getLogger(__name__)


def supervisor_node(state: AgentState) -> dict[str, Any]:
    """
    Supervisor Agent — classifies intent and generates small-talk reply.

    Reads: user_input, is_safe
    Writes: intent, small_talk_reply, nodes_visited, error
    """
    logger.info("Supervisor Agent: processing question")

    try:
        user_input = state.get("user_input", "")

        # Input validation (edge cases)
        if not user_input or not user_input.strip():
            logger.warning("Supervisor: received empty input")
            return {
                "intent": "DIABETES",
                "small_talk_reply": "",
                "nodes_visited": ["supervisor"],
                "error": "Câu hỏi không hợp lệ. Vui lòng nhập câu hỏi rõ ràng.",
            }

        if not any(c.isalnum() for c in user_input):
            logger.warning("Supervisor: received special-char-only input")
            return {
                "intent": "DIABETES",
                "small_talk_reply": "",
                "nodes_visited": ["supervisor"],
                "error": "Vui lòng nhập câu hỏi rõ ràng bằng văn bản.",
            }

        # UC-009: Format chat history for context
        chat_history = state.get("chat_history", [])
        print(f"chatOriginHistory: {chat_history}")
        history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role = "user" if msg.type == "human" else "assistant"
                history_lines.append(f"  {role}: {msg.content}")
            history_text = "\n".join(history_lines)

        # Classify intent using ChatGroq
        history_section = f"\nLịch sử hội thoại:\n{history_text}\n" if history_text else ""
        prompt = f"""Phân loại tin nhắn sau thành MỘT trong hai nhãn:
- SMALL_TALK: chào hỏi, cảm ơn, tạm biệt, trò chuyện thông thường, hỏi về cách thức hoạt động của hệ thống, hoặc các câu hỏi thông thường, không liên quan đến các thông tin y tế
- DIABETES: câu hỏi hoặc yêu cầu thông tin về bệnh tiểu đường / sức khỏe

Nếu là SMALL_TALK thì trả lời luôn bằng câu trả lời giao tiếp thông thường, không cần thực hiện tìm kiếm vector.
Nếu không phải thì trả về duy nhất một từ: DIABETES.
{history_section}
Tin nhắn: "{user_input}"
"""

        llm = ChatGroq(
            model_name=GENERATIVE_MODEL,
            temperature=0.7,
        )

        response = llm.invoke(prompt)
        response_text = response.content.strip()

        if "DIABETES" in response_text.upper():
            # Diabetes / health question → route to RAG
            intent = "DIABETES"
            small_talk_reply = ""
            logger.info(
                f"Supervisor: classified as DIABETES → routing to RAG Agent "
                f"(length={len(user_input)} chars)"
            )
        else:
            # Small talk → bypass RAG, use the LLM's inline reply
            intent = "SMALL_TALK"
            small_talk_reply = response_text
            logger.info(
                f"Supervisor: classified as SMALL_TALK → bypassing RAG "
                f"(reply_length={len(small_talk_reply)} chars)"
            )

        return {
            "intent": intent,
            "small_talk_reply": small_talk_reply,
            "nodes_visited": ["supervisor"],
        }

    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}", exc_info=True)
        # Default to DIABETES on error (fail-safe → prefer RAG)
        return {
            "intent": "DIABETES",
            "small_talk_reply": "",
            "nodes_visited": ["supervisor"],
            "error": f"Supervisor error: {str(e)}",
        }
