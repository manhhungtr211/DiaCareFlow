"""
Supervisor Agent node for the Multi-Agent pipeline (UC-012).

Role change from UC-010:
  - Previously: classified intent (SMALL_TALK vs DIABETES) and set rag_context.
  - Now (UC-012): classifies intent, handles SMALL_TALK directly,
    and for DIABETES questions dispatches fan-out via Send to 3 parallel sub-agents:
      factor_agent, suggestion_agent, harm_sub_agent.

The Send-based fan-out is wired in graph.py (T015). This node's job is to:
  1. Classify intent using LLM (SMALL_TALK vs DIABETES).
  2. If SMALL_TALK: generate reply inline and write to small_talk_reply.
  3. If DIABETES: just set intent=DIABETES (graph.py dispatch_sub_agents handles fan-out).

Errors are isolated: any exception defaults intent to DIABETES (fail-safe).
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
    Supervisor Agent — classify intent and handle SMALL_TALK inline.

    For DIABETES questions: sets intent="DIABETES" so graph.py can fan-out
    to the 3 sub-agents via the Send API (wired in T015).

    Reads: user_input, chat_history
    Writes: intent, small_talk_reply, nodes_visited, errors
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
                "errors": ["Supervisor: câu hỏi không hợp lệ — input rỗng"],
            }

        if not any(c.isalnum() for c in user_input):
            logger.warning("Supervisor: received special-char-only input")
            return {
                "intent": "DIABETES",
                "small_talk_reply": "",
                "nodes_visited": ["supervisor"],
                "errors": ["Supervisor: câu hỏi không hợp lệ — chỉ chứa ký tự đặc biệt"],
            }

        # UC-009: Format chat history for context
        chat_history = state.get("chat_history", [])
        history_text = ""
        if chat_history:
            history_lines = []
            for msg in chat_history:
                role = "user" if msg.type == "human" else "assistant"
                history_lines.append(f"  {role}: {msg.content}")
            history_text = "\n".join(history_lines)

        history_section = f"\nLịch sử hội thoại:\n{history_text}\n" if history_text else ""
#         prompt = f"""Phân loại tin nhắn sau thành MỘT trong hai nhãn:
# - SMALL_TALK: chào hỏi, cảm ơn, tạm biệt, trò chuyện thông thường, hỏi về cách thức hoạt động của hệ thống, hoặc các câu hỏi thông thường, không liên quan đến các thông tin y tế
# - DIABETES: câu hỏi hoặc yêu cầu thông tin về bệnh tiểu đường / sức khỏe

# Trả về KẾT QUẢ DƯỚI DẠNG JSON với cấu trúc sau:
# {{
#   "intent": "SMALL_TALK" hoặc "DIABETES",
#   "small_talk_reply": "Câu trả lời trực tiếp nếu intent là SMALL_TALK, ngược lại để chuỗi rỗng",
#   "factor_question": "Nếu intent là DIABETES: Câu hỏi phụ tập trung vào việc tìm hiểu nguyên nhân, cơ chế bệnh sinh của vấn đề người dùng hỏi. Ngược lại để chuỗi rỗng",
#   "suggestion_question": "Nếu intent là DIABETES: Câu hỏi phụ tập trung vào việc tìm giải pháp, lời khuyên thực tế cho người dùng. Ngược lại để chuỗi rỗng",
#   "harm_question": "Nếu intent là DIABETES: Câu hỏi phụ tập trung vào việc đánh giá rủi ro, cảnh báo an toàn sức khỏe. Ngược lại để chuỗi rỗng"
# }}

# {history_section}
# Tin nhắn: "{user_input}"
# KẾT QUẢ JSON:
# """
        prompt = f"""Bạn là Supervisor Agent trong multi-agent system hỗ trợ người dùng giải đáp các thắc mắc liên quan đến bệnh tiểu đường. "
"Bạn chịu trách nhiệm phân tích thông tin nhập mới nhất của người dùng và toàn bộ lịch sử trò chuyện để đưa ra quyết định có cấu trúc, một bước duy nhất, hướng dẫn phần còn lại của hệ thống.\n\n"
"Trách nhiệm:\n"
"1. Hiểu ý định của người dùng dựa trên tin nhắn mới nhất của họ và toàn bộ lịch sử cuộc trò chuyện.\n"
"2. Quyết định hành động tốt nhất tiếp theo dựa trên ngữ cảnh hiện tại:\n"
"- Nếu câu hỏi mơ hồ, chung chung hoặc thiếu các chi tiết cần thiết, hãy yêu cầu làm rõ.\n"
"- Nếu hệ thống cần thu thập thêm thông tin trước khi trả lời, hãy giao nhiệm vụ cụ thể cho một hoặc nhiều đặc vụ.\n"
"- Nếu đã có đủ ngữ cảnh - hoặc nếu câu hỏi đơn giản (ví dụ: lời chào, trò chuyện xã giao) - hãy báo hiệu rằng hệ thống nên tiến hành trả lời cuối cùng.\n\n"
"Các đặc vụ hiện có và vai trò của họ:\n"
"- `suggestion_agent`: Cung cấp các đề xuất cụ thể, có thể thực hiện được liên quan đến bệnh tiểu đường. \n"
"- `harm_agent`: Mô tả các tác hại và ảnh hưởng tiêu cực do bệnh tiểu đường gây ra.\n"
"- `factor_agent`: Xác định các yếu tố góp phần gây ra bệnh tiểu đường.\n"
"- `response_agent`: Đưa ra phản hồi cuối cùng khi không cần làm rõ thêm hoặc nhiệm vụ của tác nhân.\n\n"

Định dạng đầu ra:\n"
Trả về **chỉ một** trong các đầu ra có cấu trúc sau:\n\n"
Tùy chọn 1 - Yêu cầu làm rõ:\n"
- `follow_up_question`: Một câu hỏi tiếp theo rõ ràng. Nếu sử dụng trường này, không nên bao gồm các trường khác.\n\n"
Tùy chọn 2 - Báo hiệu sẵn sàng phản hồi:\n"
- `should_response`: Chỉ đặt thành True khi hệ thống có đủ thông tin để gọi `response_agent`. Không nên bao gồm các trường khác.\n\n"
Tùy chọn 3 - Giao nhiệm vụ cho các tác nhân:\n"
- Cung cấp bất kỳ sự kết hợp nào của:\n"    
- `suggestion_agent`: Một tác vụ độc lập cho tác nhân đề xuất, hoặc None.\n"
- `harm_agent`: Một tác vụ độc lập cho tác nhân gây hại, hoặc None.\n"
- `factor_agent`: Một tác vụ độc lập cho tác nhân yếu tố, hoặc None.""
History: {history_section}
Message: "{user_input}"
"""
        llm = ChatGroq(
            model_name=GENERATIVE_MODEL,
            temperature=0.7,
        )

        response = llm.invoke(prompt, config={"configurable": {"thread_id": thread_id}})
        response_text = response.content.strip()

        # Extract JSON from response
        import json
        import re
        
        # Try to find JSON block in case LLM outputs extra text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
            
        try:
            parsed = json.loads(json_str)
            intent = parsed.get("intent", "DIABETES")
            small_talk_reply = parsed.get("small_talk_reply", "")
            follow_up_question = parsed.get("follow_up_question, ")
            factor_question = parsed.get("factor_question", user_input)
            suggestion_question = parsed.get("suggestion_question", user_input)
            harm_question = parsed.get("harm_question", user_input)
        except json.JSONDecodeError:
            logger.warning("Supervisor: Failed to parse JSON, falling back to DIABETES intent")
            intent = "DIABETES"
            small_talk_reply = ""
            factor_question = user_input
            suggestion_question = user_input
            harm_question = user_input

        if "DIABETES" in intent.upper():
            intent = "DIABETES"
            logger.info(
                f"Supervisor: classified as DIABETES → dispatching to sub-agents "
                f"(length={len(user_input)} chars)"
            )
        else:
            intent = "SMALL_TALK"
            logger.info(
                f"Supervisor: classified as SMALL_TALK → bypassing sub-agents "
                f"(reply_length={len(small_talk_reply)} chars)"
            )

        return {
            "intent": intent,
            "small_talk_reply": small_talk_reply,
            "factor_question": factor_question,
            "suggestion_question": suggestion_question,
            "harm_question": harm_question,
            "nodes_visited": ["supervisor"],
        }

    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}", exc_info=True)
        # Default to DIABETES on error (fail-safe → prefer sub-agents)
        return {
            "intent": "DIABETES",
            "small_talk_reply": "",
            "factor_question": state.get("user_input", ""),
            "suggestion_question": state.get("user_input", ""),
            "harm_question": state.get("user_input", ""),
            "nodes_visited": ["supervisor"],
            "errors": [f"Supervisor error: {str(e)}"],
        }
