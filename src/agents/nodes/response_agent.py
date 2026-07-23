"""
Response Agent node for the LangGraph pipeline (UC-012).

Handles three paths:
  - UNSAFE path: returns the triage refusal message directly (no LLM call needed,
    suggestion_context.refusal_message already set by triage_agent).
  - SMALL_TALK path: returns the supervisor's pre-generated reply (no RAG/sub-agents).
  - DIABETES path (main): synthesizes final answer from the 3 sub-agent summaries:
      factor_results[0]     → root cause / mechanism
      suggestion_results[0] → practical solutions
      harm_results[0]     → risk / safety warnings

    Gracefully handles missing sub-agent results (node error → empty list).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_groq import ChatGroq

from src.agents.state import AgentState
from src.config import GENERATIVE_MODEL

logger = logging.getLogger(__name__)

_RESPONSE_SYSTEM_PROMPT = """Bạn là Response Agent trong hệ thống multi-agent được thiết kế để hỗ trợ người dùng giải đáp các thắc mắc liên quan đến bệnh tiểu đường.

Bạn được cung cấp:
- Lịch sử trò chuyện gần nhất giữa người dùng và hệ thống.
- Một danh sách các ngữ cảnh được trích xuất từ các Agent chuyên môn (Factor, Suggestion, Harm).

Nhiệm vụ của bạn là tạo ra một phản hồi tự nhiên, hữu ích, có cơ sở và toàn diện cho thông tin đầu vào mới nhất của người dùng dựa trên lịch sử trò chuyện và ngữ cảnh có sẵn.

Hướng dẫn:
1. Đọc kỹ toàn bộ lịch sử trò chuyện để hiểu nhu cầu và các tương tác trước đó của người dùng.
2. Nếu thông tin đầu vào mới nhất của người dùng là chung chung, mang tính hội thoại (ví dụ: lời chào) hoặc đơn giản, hãy phản hồi trực tiếp mà không sử dụng các ngữ cảnh được trích xuất.
3. Nếu có các ngữ cảnh được trích xuất, hãy tổng hợp chúng để xây dựng một phản hồi rõ ràng, đầy đủ thông tin và toàn diện:
   - Giải quyết tất cả các khía cạnh liên quan đến câu hỏi của người dùng dựa trên thông tin có sẵn.
   - Tích hợp và kết nối thông tin chi tiết từ nhiều ngữ cảnh khi thích hợp.
   - Tránh chỉ liệt kê nội dung; thay vào đó, hãy giải thích và diễn giải để người dùng hiểu đầy đủ.
4. Không bịa đặt bất kỳ thông tin nào. Chỉ sử dụng những gì có trong lịch sử trò chuyện hoặc ngữ cảnh được trích xuất, hoặc dựa vào kiến thức y khoa chung đã được thiết lập tốt.
5. Duy trì giọng điệu đồng cảm và hỗ trợ, đặc biệt khi giải quyết các vấn đề liên quan đến sức khỏe.
6. Nếu không có ngữ cảnh liên quan và câu hỏi của người dùng quá cụ thể, hãy lịch sự cho người dùng biết rằng có thể cần thêm thông tin.
7. Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu.
"""

def response_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Response Agent — generate final answer from aggregated sub-agent results.

    For UNSAFE: read refusal_message from suggestion_context (set by triage_agent).
    For SMALL_TALK: return small_talk_reply from supervisor.
    For DIABETES: synthesize from factor_results, suggestion_results, harm_results.

    Reads: is_safe, intent, small_talk_reply, suggestion_context,
           factor_results, suggestion_results, harm_results,
           user_input, chat_history, errors
    Writes: suggestion_context, nodes_visited, errors
    """
    logger.info("Response Agent: generating final answer")

    try:
        is_safe = state.get("is_safe", True)
        intent = state.get("intent", "DIABETES")

        # --- UNSAFE path: triage already set response_context.refusal_message ---
        if not is_safe:
            existing = state.get("response_context", {})
            refusal_msg = existing.get(
                "refusal_message",
                "Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi hỗ trợ.",
            )
            logger.info("Response Agent: returning refusal (unsafe path)")
            return {
                "response_context": {
                    "final_answer": refusal_msg,
                    "refusal_message": refusal_msg,
                    "sources": [],
                    "is_refused": True,
                    "refuse_reason": str(state.get("triage_results", "")),
                },
                "nodes_visited": ["response_agent"],
            }

        # --- SMALL_TALK path: return supervisor's inline reply ---
        if intent == "SMALL_TALK":
            small_talk_reply = state.get("small_talk_reply", "")
            logger.info(
                f"Response Agent: returning small-talk reply "
                f"(length={len(small_talk_reply)} chars)"
            )
            return {
                "response_context": {
                    "final_answer": small_talk_reply,
                    "sources": [],
                    "is_refused": False,
                    "refuse_reason": None,
                },
                "nodes_visited": ["response_agent"],
            }

        # --- DIABETES path: synthesize from sub-agent results ---
        user_input = state.get("user_input", "")
        factor_results = state.get("factor_results", [])
        suggestion_results = state.get("suggestion_results", [])
        harm_results = state.get("harm_results", [])
        sub_errors = state.get("errors", [])
        chat_history = state.get("chat_history", [])

        # Extract summaries (gracefully handle missing results)
        factor_summary = factor_results[0].get("factor_summary", "") if factor_results else ""
        suggestion_summary = (
            suggestion_results[0].get("suggestion_summary", "") if suggestion_results else ""
        )
        harm_summary = harm_results[0].get("harm_summary", "") if harm_results else ""

        # Collect sources from sub-agents
        all_sources: list[dict] = []
        if factor_results:
            all_sources.extend(factor_results[0].get("sources", []))
        if suggestion_results:
            all_sources.extend(suggestion_results[0].get("sources", []))

        # Build context section for LLM prompt
        context_parts = []
        if factor_summary:
            context_parts.append(f"**Nguyên nhân / Yếu tô gây ra:**\n{factor_summary}")
        if suggestion_summary:
            context_parts.append(f"**Giải pháp thực tế:**\n{suggestion_summary}")
        if harm_summary:
            context_parts.append(f"**Tác hại và ảnh hưởng gây ra:**\n{harm_summary}")

        if not context_parts:
            # All sub-agents failed
            error_note = "; ".join(sub_errors) if sub_errors else "Không có thông tin từ các Agent"
            logger.warning(f"Response Agent: all sub-agents returned empty results. Errors: {error_note}")
            return {
                "response_context": {
                    "final_answer": (
                        "Xin lỗi, hệ thống không thể thu thập đủ thông tin để trả lời câu hỏi của bạn. "
                        "Vui lòng thử lại sau hoặc đặt câu hỏi khác."
                    ),
                    "sources": [],
                    "is_refused": False,
                    "refuse_reason": None,
                },
                "nodes_visited": ["response_agent"],
                "errors": [f"Response Agent: all sub-agents empty"],
            }

        context_text = "\n\n".join(context_parts)

        prompt = f"""{_RESPONSE_SYSTEM_PROMPT}
Lịch sử trò chuyện:
{chat_history}

Thông tin từ các chuyên gia:
{context_text}

Câu hỏi của người dùng: {user_input}

Câu trả lời tổng hợp:"""

        llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.4)
        response = llm.invoke(prompt)
        final_answer = response.content.strip()

        logger.info(
            f"Response Agent: generated final answer "
            f"(length={len(final_answer)} chars, sources={len(all_sources)})"
        )

        response_context = {
            "final_answer": final_answer,
            "sources": all_sources,
            "is_refused": False,
            "refuse_reason": None,
        }

        result = {
            "response_context": response_context,
            "nodes_visited": ["response_agent"],
        }
        if sub_errors:
            result["errors"] = [f"Response Agent: partial sub-agent errors: {sub_errors}"]

        return result

    except Exception as e:
        logger.error(f"Response Agent error: {e}", exc_info=True)
        return {
            "response_context": {
                "final_answer": "Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại sau.",
                "sources": [],
                "is_refused": False,
                "refuse_reason": None,
            },
            "nodes_visited": ["response_agent"],
            "errors": [f"Response Agent error: {str(e)}"],
        }
