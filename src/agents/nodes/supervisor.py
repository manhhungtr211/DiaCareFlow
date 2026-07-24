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
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq

from src.agents.state import AgentState
from src.config import ROUTING_MODEL

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
    logger.info(f"Supervisor Agent Input: {state.get('user_input', '')}")

    try:
        user_input = state.get("user_input", "")

        # Input validation (edge cases)
        if not user_input or not user_input.strip():
            logger.warning("Supervisor: received empty input")
            output = {
                "intent": "DIABETES",
                "small_talk_reply": "",
                "nodes_visited": ["supervisor"],
                "errors": ["Supervisor: câu hỏi không hợp lệ — input rỗng"],
            }
            logger.info(f"Supervisor Agent Output: {output}")
            return output

        if not any(c.isalnum() for c in user_input):
            logger.warning("Supervisor: received special-char-only input")
            output = {
                "intent": "DIABETES",
                "small_talk_reply": "",
                "nodes_visited": ["supervisor"],
                "errors": ["Supervisor: câu hỏi không hợp lệ — chỉ chứa ký tự đặc biệt"],
            }
            logger.info(f"Supervisor Agent Output: {output}")
            return output

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
Tùy chọn 1 - Báo hiệu sẵn sàng phản hồi:\n"
- `should_response`: Chỉ đặt thành True khi đây là một câu hỏi small-talk thông thường, không liên quan đến bệnh. Không nên bao gồm các trường khác.(chỉ đặt cho các câu hỏi thông thường, xã giao)\n\n"
Tùy chọn 2 - Giao nhiệm vụ cho các tác nhân:\n"
- Cung cấp bất kỳ sự kết hợp nào của:\n"    
- `should_response`: đặt là false
- `suggestion_agent`: Một tác vụ độc lập cho tác nhân đề xuất, hoặc None. \n"
- `harm_agent`: Một tác vụ độc lập cho tác nhân gây hại, hoặc None. \n"
- `factor_agent`: Một tác vụ độc lập cho tác nhân yếu tố, hoặc None. \n"
Sử dụng tiếng Việt

History: {history_section}
Message: "{user_input}"
"""   
        logger.info(f"history: {history_section}")
        
        # Use gpt-oss-20b for Supervisor routing
        llm = ChatGroq(
            model_name=ROUTING_MODEL,
            temperature=0.0
        )

        response = llm.invoke(prompt)
        response_text = response.content.strip()

        # Extract JSON from response
        import json
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
            
        try:
            parsed = json.loads(json_str)
            follow_up_question = parsed.get("follow_up_question", "")
            should_response = parsed.get("should_response", False)
            factor_task = parsed.get("factor_agent", "")
            suggestion_task = parsed.get("suggestion_agent", "")
            harm_task = parsed.get("harm_agent", "")
            
            # Normalize nulls to empty strings
            if factor_task is None: factor_task = ""
            if suggestion_task is None: suggestion_task = ""
            if harm_task is None: harm_task = ""
            if follow_up_question is None: follow_up_question = ""
        except json.JSONDecodeError:
            logger.warning("Supervisor: Failed to parse JSON, falling back to full sub-agents dispatch")
            follow_up_question = ""
            should_response = False
            factor_task = user_input
            suggestion_task = user_input
            harm_task = user_input

        if follow_up_question:
            logger.info("Supervisor: classified as FOLLOW_UP_QUESTION")
        elif should_response:
            logger.info("Supervisor: classified as SHOULD_RESPONSE (bypass sub-agents)")
        else:
            logger.info("Supervisor: classified as FAN-OUT to sub-agents")

        output = {
            "follow_up_question": follow_up_question,
            "should_response": should_response,
            "factor_task": factor_task,
            "suggestion_task": suggestion_task,
            "harm_task": harm_task,
            "nodes_visited": ["supervisor"],
        }
        
        return output

    except Exception as e:
        logger.error(f"Supervisor Agent error: {e}", exc_info=True)
        # Default to sub-agents on error (fail-safe)
        return {
            "follow_up_question": "",
            "should_response": False,
            "factor_task": state.get("user_input", ""),
            "suggestion_task": state.get("user_input", ""),
            "harm_task": state.get("user_input", ""),
            "nodes_visited": ["supervisor"],
            "errors": [f"Supervisor error: {str(e)}"],
        }
