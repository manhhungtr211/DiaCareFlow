from __future__ import annotations
import logging
from langchain_groq import ChatGroq

from src.config import GENERATIVE_MODEL
from src.tools.rag.qa.data_models import Answer, Query, RetrievedContext

logger = logging.getLogger(__name__)

def generate(query: Query, context: RetrievedContext, chat_history: list | None = None) -> Answer:
    """
    Generate an answer using LLM based on the retrieved context.

    Args:
        query: The user's query.
        context: Retrieved document chunks from RAG.
        chat_history: Optional list of BaseMessage objects for conversational context (UC-009).
    """
    
    if not context.chunks:
        logger.info("No context chunks provided to generator.")
        return Answer(
            text="Tôi không tìm thấy thông tin về chủ đề này trong tài liệu hiện có.",
            sources=[],
            is_refused=False
        )

    # 1. Prepare context text
    context_text = "\n\n".join([f"--- Đoạn {i+1} ---\n{chunk.content}" for i, chunk in enumerate(context.chunks)])
    
    print("\n" + "="*50)
    print("KẾT QUẢ RETRIEVED TỪ VECTOR DB:")
    print(context_text)
    print("="*50 + "\n")

    # UC-009: Format chat history for conversational context
    history_section = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "user" if msg.type == "human" else "assistant"
            history_lines.append(f"  {role}: {msg.content}")
        history_text = "\n".join(history_lines)
        
        print("\n" + "="*50)
        print("LỊCH SỬ HỘI THOẠI (CHAT HISTORY):")
        print(history_text)
        print("="*50 + "\n")

        history_section = f"""
Lịch sử hội thoại:
{history_text}
"""
    
    # 2. Build prompt
    prompt = f"""
Bạn là một trợ lý y tế chuyên về bệnh tiểu đường. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng DỰA VÀO phần tài liệu được cung cấp dưới đây.

QUY TẮC QUAN TRỌNG:
1. CHỈ sử dụng thông tin có trong phần Tài liệu cung cấp. Không tự bịa đặt hoặc dùng kiến thức bên ngoài.
2. Nếu Tài liệu không chứa thông tin để trả lời câu hỏi, hãy nói rõ: "Tôi không tìm thấy thông tin về chủ đề này trong tài liệu hiện có."
3. Trả lời bằng ngôn ngữ phổ thông, dễ hiểu, rõ ràng.
4. Sử dụng lịch sử hội thoại (nếu có) để hiểu ngữ cảnh của câu hỏi hiện tại (ví dụ: đại từ "đó", "nó" ám chỉ điều gì).
{history_section}
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
        print("LLM RAW RESPONSE:", response)
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
