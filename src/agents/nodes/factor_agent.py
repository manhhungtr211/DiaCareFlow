"""
Factor Agent node for the Multi-Agent pipeline (UC-012).

Analyzes the root cause / mechanism of the user's health question.
Tool selection is determined via a lightweight LLM decision:
  - Primary: retrieve() (RAG) — for medical guidelines and deep medical knowledge.
  - Fallback: web_search() — when RAG returns no chunks.

Output written to state.factor_results (Annotated list, fan-in reducer).
Errors are captured in state.errors; node never raises.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_groq import ChatGroq

from src.agents.state import AgentState
from src.config import GENERATIVE_MODEL
from src.tools.rag.qa.data_models import Query
from src.tools.rag.qa.retriever import retrieve
from src.tools.web._api import web_search

logger = logging.getLogger(__name__)

# _FACTOR_SYSTEM_PROMPT = """Bạn là chuyên gia y khoa chuyên phân tích nguyên nhân và cơ chế bệnh sinh.
# Dựa vào tài liệu tham khảo được cung cấp, hãy trả lời ngắn gọn và chính xác:
# - Nguyên nhân / cơ chế liên quan đến câu hỏi của người dùng là gì?
# - Chỉ trình bày những điểm chính, KHÔNG sáng tạo thêm thông tin ngoài tài liệu.
# - Trả lời bằng tiếng Việt, tối đa 3-4 câu."""

_FACTOR_SYSTEM_PROMPT = """Bạn là Task Handler của Factor Agent. Vai trò của bạn là tạo ra các truy vấn con hiệu quả giúp truy xuất "
"thông tin chất lượng cao và phù hợp - từ bộ nhớ cục bộ hoặc tìm kiếm trên web - để hỗ trợ trả lời một nhiệm vụ liên quan đến chứng mất ngủ.\n\n"
"Bạn được giao:\n"
"- Nhiệm vụ: câu hỏi chính cần được trả lời.\n"
"Công việc của bạn là:\n"
"1. Hiểu kỹ nhiệm vụ và loại thông tin mà nó có thể cần.\n"
"2. Nếu có phản hồi, hãy phân tích nó để xác định các khoảng trống hoặc điểm yếu trong quá trình truy xuất trước đó.\n"
"3. Tạo tối đa 2 *truy vấn con* rõ ràng và tập trung hướng dẫn hệ thống truy xuất thông tin tốt hơn hoặc đầy đủ hơn để hỗ trợ trả lời nhiệm vụ.\n\n"
"Hướng dẫn:\n"
"- Chỉ chia nhỏ hoặc định dạng lại nhiệm vụ nếu làm như vậy sẽ cải thiện hiệu quả truy xuất; Nếu không, hãy tái sử dụng hoặc tinh chỉnh nhẹ nhiệm vụ đó thành một truy vấn con duy nhất.\n"
"- Mỗi truy vấn con phải cụ thể, không trùng lặp và trực tiếp nhằm mục đích làm phong phú thêm thông tin cần thiết cho nhiệm vụ.\n"
"- Phản hồi nên được sử dụng để hướng dẫn việc tinh chỉnh của bạn — đặc biệt khi nó làm nổi bật cách diễn đạt mơ hồ, góc nhìn bị bỏ sót hoặc kết quả không liên quan.\n"
"- Quá trình này có thể lặp lại nhiều lần, với phản hồi được cập nhật mỗi lần. Nhiệm vụ của bạn là cải thiện dần khả năng truy xuất trong mỗi vòng lặp bằng cách tạo ra các truy vấn con hiệu quả hơn."
"""

def factor_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Factor Agent — analyze root cause / mechanism.

    Tool decision:
      1. Call retrieve() (RAG).
      2. If RAG returns 0 chunks, fall back to web_search().
      3. Call LLM with the collected context.

    Reads: user_input
    Writes: factor_results (appended), nodes_visited (appended), errors (appended on failure)
    """
    logger.info("Factor Agent: analyzing root cause")

    try:
        user_input = state.get("user_input", "")

        # --- Step 1: Try RAG ---
        context_text = ""
        sources: list[dict] = []

        try:
            query = Query(text=user_input)
            retrieved = retrieve(query)
            if retrieved.chunks:
                context_text = "\n\n".join(
                    f"[Nguồn: {c.source}]\n{c.content}" for c in retrieved.chunks
                )
                sources = [
                    {"content": c.content, "source": c.source, "score": c.score}
                    for c in retrieved.chunks
                ]
                logger.info(f"Factor Agent: RAG returned {len(retrieved.chunks)} chunks")
            else:
                logger.info("Factor Agent: RAG returned 0 chunks, falling back to web_search")
        except Exception as rag_err:
            logger.warning(f"Factor Agent: RAG failed ({rag_err}), falling back to web_search")

        # --- Step 2: Fallback to web_search if no context yet ---
        if not context_text:
            try:
                result = asyncio.run(web_search(user_input))
                if result.found and result.combined_text:
                    context_text = result.combined_text[:3000]  # limit tokens
                    logger.info("Factor Agent: web_search fallback succeeded")
            except Exception as web_err:
                logger.warning(f"Factor Agent: web_search fallback also failed: {web_err}")

        # --- Step 3: LLM summarization ---
        if context_text:
            extractor_prompt = f"""Bạn là một Extractor Agent trong hệ thống multi-agent hỗ trợ trả lời các truy vấn liên quan đến bệnh tiểu đường.

Nhiệm vụ cần trả lời: {user_input}

Danh sách Ngữ cảnh Đã Truy xuất:
{context_text}

Công việc của bạn là:
1. Đọc và hiểu nhiệm vụ.
2. Xem xét cẩn thận từng ngữ cảnh được cung cấp.
3. Chỉ trích xuất thông tin có liên quan và hữu ích để trả lời nhiệm vụ — tập trung vào nguyên nhân, yếu tố, cơ chế liên quan đến bệnh tiểu đường.
4. Loại bỏ bất kỳ nội dung nào rõ ràng không liên quan, dư thừa, hoặc không cung cấp thông tin.
5. Đối với ngữ cảnh tìm kiếm trên web, xác định và trích xuất bất kỳ phần nào thực sự hữu ích.

Đối với mỗi nguồn, hãy trả về:
- **URL hoặc Nguồn**
- **Ngữ cảnh được trích xuất**: một bản tóm tắt ngắn gọn, liên quan đến nhiệm vụ về thông tin từ nguồn đó.

Chỉ xuất ra các mục được trích xuất cuối cùng. Không bao gồm giải thích, các bướng lập luận hoặc bình luận bổ sung.
"""
            llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.1)
            response = llm.invoke(extractor_prompt)
            factor_summary = response.content.strip()

            logger.info(f"Factor Agent: generated summary (length={len(factor_summary)} chars)")

            return {
                "factor_results": [{"factor_summary": factor_summary, "sources": sources}],
                "nodes_visited": ["factor_agent"],
            }
        else:
            # T037: No context available — return empty results (never return "", LangGraph requires dict)
            logger.warning("Factor Agent: no context found from any tool")
            return {
                "factor_results": [],
                "nodes_visited": ["factor_agent"],
            }

    except Exception as e:
        logger.error(f"Factor Agent error: {e}", exc_info=True)
        return {
            "factor_results": [],
            "nodes_visited": ["factor_agent"],
            "errors": [f"Factor Agent error: {str(e)}"],
        }
