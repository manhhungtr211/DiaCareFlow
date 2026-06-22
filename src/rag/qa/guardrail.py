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
Nhiệm vụ của bạn là:
1. Xác định xem câu hỏi của người dùng có liên quan đến sức khỏe, y tế, cụ thể là bệnh tiểu đường hoặc các vấn đề sức khỏe chung hay không.
2. Xác định xem câu hỏi có chứa từ khóa nhạy cảm như: thuốc, kê đơn, bệnh viện, cấp cứu, v.v. không.
Nếu câu hỏi THOẢ MÃN điều kiện 1 VÀ KHÔNG chứa từ khóa nhạy cảm, hãy trả lời duy nhất: YES
Nếu câu hỏi KHÔNG liên quan y tế (ví dụ: thời tiết, toán học...) HOẶC CÓ chứa các từ nhạy cảm, hãy trả lời duy nhất: NO

Câu hỏi: "{query.text}"
"""
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        
        if "YES" in answer:
            return GuardrailResult(is_safe=True)
        else:
            return GuardrailResult(
                is_safe=False,
                reason="Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi hỗ trợ hoặc yêu cầu tư vấn y tế chuyên sâu (kê đơn, chẩn đoán, cấp cứu). Vui lòng tham khảo ý kiến bác sĩ hoặc gọi cấp cứu 115 trong trường hợp khẩn cấp."
            )

    except Exception as e:
        logger.error(f"Error in guardrail LLM check: {e}")
        # Default to safe if guardrail fails, or could default to unsafe
        return GuardrailResult(is_safe=True)