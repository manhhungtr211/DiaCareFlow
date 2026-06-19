from __future__ import annotations
import logging
from langchain_groq import ChatGroq

from src.config import GENERATIVE_MODEL
from src.rag.qa.data_models import Answer, Query, RetrievedContext

logger = logging.getLogger(__name__)

def generate(query: Query, context: RetrievedContext) -> Answer:
    """Generate an answer using Gemini based on the retrieved context."""
    
    if not context.chunks:
        logger.info("No context chunks provided to generator.")
        return Answer(
            text="Tôi không tìm thấy thông tin về chủ đề này trong tài liệu hiện có.",
            sources=[],
            is_refused=False
        )

    # 1. Prepare context text
    context_text = "\n\n".join([f"--- Đoạn {i+1} ---\n{chunk.content}" for i, chunk in enumerate(context.chunks)])
    
    # 2. Build prompt
    prompt = f"""
Bạn là một trợ lý y tế chuyên về bệnh tiểu đường. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng DỰA VÀO phần tài liệu được cung cấp dưới đây.

QUY TẮC QUAN TRỌNG:
1. CHỈ sử dụng thông tin có trong phần Tài liệu cung cấp. Không tự bịa đặt hoặc dùng kiến thức bên ngoài.
2. Nếu Tài liệu không chứa thông tin để trả lời câu hỏi, hãy nói rõ: "Tôi không tìm thấy thông tin về chủ đề này trong tài liệu hiện có."
3. Trả lời bằng ngôn ngữ phổ thông, dễ hiểu, rõ ràng.

Tài liệu cung cấp:
{context_text}

Câu hỏi của người dùng:
{query.text}

Câu trả lời:
"""

    # 3. Call LLM
    try:
        logger.info(f"Generating answer using {GENERATIVE_MODEL}")
        llm = ChatGroq(
            model_name=GENERATIVE_MODEL,
            temperature=0.2  # Low temperature for more factual responses
        )
        
        response = llm.invoke(prompt)
        answer_text = response.content.strip()
        
        return Answer(
            text=answer_text,
            sources=context.chunks,
            is_refused=False
        )
        
    except Exception as e:
        logger.error(f"Failed to generate answer: {e}")
        return Answer(
            text="Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại sau.",
            sources=[],
            is_refused=False
        )
