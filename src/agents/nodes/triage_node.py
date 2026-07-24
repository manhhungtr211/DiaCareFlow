"""
Triage Agent node for the LangGraph pipeline.

Wraps src/rag/qa/guardrail.py to evaluate question safety and classify
into SafetyCategory (SAFE, PRESCRIPTION, DIAGNOSIS, EMERGENCY).
This is the FIRST node in the graph — runs before Supervisor.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState, SafetyCategory
from src.config import TOOL_MODEL
from src.tools.rag.qa.data_models import Query, GuardrailResult
from src.tools.rag.qa.guardrail import check_guardrail

logger = logging.getLogger(__name__)

# Refusal messages mapped to SafetyCategory (used by US2 T011)
REFUSAL_MESSAGES: dict[SafetyCategory, str] = {
    SafetyCategory.PRESCRIPTION: (
        "Xin lỗi, tôi không thể kê đơn thuốc. "
        "Vui lòng tham khảo ý kiến bác sĩ."
    ),
    SafetyCategory.DIAGNOSIS: (
        "Xin lỗi, tôi không thể chẩn đoán bệnh. "
        "Vui lòng đến cơ sở y tế."
    ),
    SafetyCategory.EMERGENCY: (
        "⚠️ Tình huống khẩn cấp! "
        "Vui lòng gọi 115 hoặc đến phòng cấp cứu ngay."
    ),
}


def triage_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Evaluate question safety using the existing guardrail module.

    Reads: user_input
    Writes: is_safe, triage_results, response_context (refusal_message if unsafe),
            nodes_visited, errors
    """
    logger.info("Triage Agent: evaluating question safety")
    logger.info(f"Triage Agent Input: {state.get('user_input', '')}")

    try:
        user_input = state.get("user_input", "")

        # Validate non-empty input
        if not user_input or not user_input.strip():
            logger.warning("Triage: empty or whitespace-only input")
            output = {
                "is_safe": False,
                "triage_results": SafetyCategory.SAFE,
                "response_context": {
                    "refusal_message": "Câu hỏi không hợp lệ. Vui lòng nhập câu hỏi rõ ràng."
                },
                "nodes_visited": ["triage_agent"],
                "errors": ["Empty input"],
            }
            logger.info(f"Triage Agent Output: {output}")
            return output

        # Check for special-char-only input
        if not any(c.isalnum() for c in user_input):
            logger.warning("Triage: special-char-only input")
            output = {
                "is_safe": False,
                "triage_results": SafetyCategory.SAFE,
                "response_context": {
                    "refusal_message": "Vui lòng nhập câu hỏi rõ ràng bằng văn bản."
                },
                "nodes_visited": ["triage_agent"],
                "errors": ["Special characters only"],
            }
            logger.info(f"Triage Agent Output: {output}")
            return output

        # Use Gemini 2.0 Flash for Triage
        llm = ChatGoogleGenerativeAI(model=TOOL_MODEL, temperature=0.0)
        
        # Invoke LLM with strict classification prompt
        logger.info("Triage Agent: checking input safety...")

        # Create Query object for guardrail
        query = Query(text=user_input)

        # Call existing guardrail
        guard_result: GuardrailResult = check_guardrail(query)

        if guard_result.is_safe:
            logger.info("Triage: question is SAFE")
            output = {
                "is_safe": True,
                "triage_results": SafetyCategory.SAFE,
                "nodes_visited": ["triage_agent"],
            }
            logger.info(f"Triage Agent Output: {output}")
            return output
        else:
            # Classify the type of harm from guardrail reason
            category = _classify_harm(guard_result.reason or "")
            refusal_msg = REFUSAL_MESSAGES.get(category, guard_result.reason or "")

            logger.info(f"Triage: question is UNSAFE ({category.value})")
            output = {
                "is_safe": False,
                "triage_results": category,
                "response_context": {"refusal_message": refusal_msg},
                "nodes_visited": ["triage_agent"],
            }
            logger.info(f"Triage Agent Output: {output}")
            return output

    except Exception as e:
        logger.error(f"Triage Agent error: {e}", exc_info=True)
        # On error, default to SAFE to avoid blocking valid questions (fail-open)
        # This matches the existing guardrail.py behavior
        output = {
            "is_safe": True,
            "triage_results": SafetyCategory.SAFE,
            "nodes_visited": ["triage_agent"],
            "errors": [f"Triage error: {str(e)}"],
        }
        logger.info(f"Triage Agent Output: {output}")
        return output


def _classify_harm(reason: str) -> SafetyCategory:
    """
    Classify the type of harm from the guardrail's reason text.

    The existing guardrail returns a generic refusal message.
    We parse keywords to determine the specific category.
    """
    reason_lower = reason.lower()

    if any(kw in reason_lower for kw in ["kê đơn", "thuốc", "prescription"]):
        return SafetyCategory.PRESCRIPTION
    elif any(kw in reason_lower for kw in ["chẩn đoán", "diagnosis"]):
        return SafetyCategory.DIAGNOSIS
    elif any(kw in reason_lower for kw in ["cấp cứu", "emergency", "115"]):
        return SafetyCategory.EMERGENCY
    else:
        # Trả về PRESCRIPTION mặc định, logic ở trên sẽ lấy guard_result.reason hoặc REFUSAL_MESSAGES
        return SafetyCategory.PRESCRIPTION