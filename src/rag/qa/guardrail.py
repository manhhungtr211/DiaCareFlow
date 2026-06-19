from __future__ import annotations
import logging
from langchain_groq import ChatGroq
from src.config import GENERATIVE_MODEL
from src.rag.qa.data_models import GuardrailResult, Query

logger = logging.getLogger(__name__)

def check_guardrail(query: Query) -> GuardrailResult:
    """Check if the user query is safe and relevant to diabetes/health."""
    
    # Simple character checks are already mostly done by Query __post_init__
    if not any(c.isalnum() for c in query.text):
        return GuardrailResult(
            is_safe=False,
            reason="Câu hỏi chỉ chứa ký tự đặc biệt. Vui lòng nhập câu hỏi bằng văn bản rõ ràng."
        )

    # Fast LLM classification
    try:
        llm = ChatGroq(
            model_name=GENERATIVE_MODEL,
            temperature=0.0
        )
        
        prompt = f"""
Bạn là một công cụ phân loại câu hỏi.
Nhiệm vụ của bạn là xác định xem câu hỏi của người dùng có liên quan đến sức khỏe, y tế, cụ thể là bệnh tiểu đường hoặc các vấn đề sức khỏe chung hay không.
Nếu CÓ liên quan (hoặc có thể liên quan), hãy trả lời duy nhất: YES
Nếu KHÔNG liên quan (ví dụ: hỏi thời tiết, toán học, lập trình, v.v.), hãy trả lời duy nhất: NO

Câu hỏi: "{query.text}"
"""
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        
        if "YES" in answer:
            return GuardrailResult(is_safe=True)
        else:
            return GuardrailResult(
                is_safe=False,
                reason="Xin lỗi, tôi chỉ hỗ trợ giải đáp các vấn đề liên quan đến bệnh tiểu đường."
            )

    except Exception as e:
        logger.error(f"Error in guardrail LLM check: {e}")
        # Default to safe if guardrail fails, or could default to unsafe
        return GuardrailResult(is_safe=True)
