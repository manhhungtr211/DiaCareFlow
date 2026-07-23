"""
Harm Sub-Agent node for the Multi-Agent pipeline (UC-012).

Evaluates health risks, contraindications, and safety warnings related to
the user's question. Focuses on what the user should be cautious about.
Tool selection logic:
  - Primary: retrieve() (RAG) — medical guidelines and safety data.
  - Fallback: web_search() — when RAG returns no chunks.

Output written to state.harm_sub_results (Annotated list, fan-in reducer).
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

# _HARM_SYSTEM_PROMPT = """Bạn là chuyên gia y tế chuyên đánh giá rủi ro và cảnh báo an toàn.
# Dựa vào tài liệu tham khảo được cung cấp, hãy trả lời ngắn gọn và cụ thể:
# - Những rủi ro, tác dụng phụ, hoặc cảnh báo nào người dùng cần lưu ý?
# - Những trường hợp nào cần tham khảo ý kiến bác sĩ ngay?
# - KHÔNG sáng tạo thêm thông tin ngoài tài liệu.
# - Trả lời bằng tiếng Việt, tối đa 3-4 câu."""
_HARM_SYSTEM_PROMPT = """"Bạn là Task Handler của Harm Agent. Vai trò của bạn là tạo ra các truy vấn con hiệu quả giúp truy xuất    
"thông tin chất lượng cao và phù hợp - từ bộ nhớ cục bộ hoặc tìm kiếm trên web - để hỗ trợ trả lời một nhiệm vụ liên quan đến chứng mất ngủ.\n\n"
"Bạn được giao:\n"
"- Nhiệm vụ: câu hỏi chính cần được trả lời.\n"

"Công việc của bạn là:\n"
"1. Hiểu kỹ nhiệm vụ và loại thông tin mà nó có thể cần.\n"
"2. Nếu có phản hồi, hãy phân tích nó để xác định các lỗ hổng hoặc điểm yếu trong quá trình truy xuất trước đó.\n"
"3. Tạo tối đa 2 *truy vấn con* rõ ràng và tập trung hướng dẫn hệ thống truy xuất thông tin tốt hơn hoặc đầy đủ hơn để hỗ trợ trả lời nhiệm vụ.\n\n"
"Hướng dẫn:\n"
"- Chỉ chia nhỏ hoặc định dạng lại nhiệm vụ nếu làm như vậy sẽ cải thiện hiệu quả truy xuất; Nếu không, hãy tái sử dụng hoặc tinh chỉnh nhẹ nhiệm vụ đó thành một truy vấn con duy nhất.\n"
"- Mỗi truy vấn con phải cụ thể, không trùng lặp và trực tiếp nhằm mục đích làm phong phú thêm thông tin cần thiết cho nhiệm vụ.\n"
"- Phản hồi nên được sử dụng để hướng dẫn việc tinh chỉnh của bạn — đặc biệt khi nó làm nổi bật cách diễn đạt mơ hồ, góc nhìn bị bỏ sót hoặc kết quả không liên quan.\n"
"- Quá trình này có thể lặp lại nhiều lần, với phản hồi được cập nhật mỗi lần. Nhiệm vụ của bạn là cải thiện dần khả năng truy xuất trong mỗi vòng lặp bằng cách tạo ra các truy vấn con hiệu quả hơn."""

def harm_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Harm Sub-Agent — assess health risks and safety warnings.

    Tool decision:
      1. Call retrieve() (RAG) — primary for guideline-based risk info.
      2. If RAG returns 0 chunks, fall back to web_search().
      3. Call LLM with the collected context.

    Reads: user_input
    Writes: harm_sub_results (appended), nodes_visited (appended), errors (appended on failure)
    """
    logger.info("Harm Sub-Agent: assessing health risks")

    try:
        user_input = state.get("user_input", "")

        # --- Step 1: Try RAG (primary) ---
        context_text = ""

        try:
            query = Query(text=user_input)
            retrieved = retrieve(query)
            if retrieved.chunks:
                context_text = "\n\n".join(
                    f"[Nguồn: {c.source}]\n{c.content}" for c in retrieved.chunks
                )
                logger.info(
                    f"Harm Sub-Agent: RAG returned {len(retrieved.chunks)} chunks"
                )
            else:
                logger.info(
                    "Harm Sub-Agent: RAG returned 0 chunks, falling back to web_search"
                )
        except Exception as rag_err:
            logger.warning(
                f"Harm Sub-Agent: RAG failed ({rag_err}), falling back to web_search"
            )

        # --- Step 2: Fallback to web_search if no context yet ---
        if not context_text:
            try:
                result = asyncio.run(web_search(user_input))
                if result.found and result.combined_text:
                    context_text = result.combined_text[:3000]  # limit tokens
                    logger.info("Harm Sub-Agent: web_search fallback succeeded")
            except Exception as web_err:
                logger.warning(
                    f"Harm Sub-Agent: web_search fallback also failed: {web_err}"
                )

        # --- Step 3: LLM summarization ---
        if context_text:
            extractor_prompt = """
            "Bạn là một Extractor Agent trong multi-agent system để hỗ trợ trả lời các truy vấn liên quan đến bệnh tiểu đường.\n\n"
            "Bạn được giao:\n"
            "- Nhiệm vụ: một câu hỏi cụ thể liên quan đến bệnh tiểu đường cần thông tin để trả lời.\n"
            "- Danh sách các Ngữ cảnh Đã Truy xuất: mỗi ngữ cảnh được truy xuất từ ​​một nguồn duy nhất thông qua RAG (cơ sở dữ liệu cục bộ) hoặc tìm kiếm trên web.\n\n"
            "Mỗi ngữ cảnh được định dạng như sau:\n```\n"
            "[Số] Tiêu đề (nếu có)\n"
            "URL (nếu từ tìm kiếm trên web) hoặc Nguồn (nếu từ RAG)\n"
            "Mô tả (nếu từ tìm kiếm trên web)\n"
            "Ngữ cảnh Đã Truy xuất\n```\n\n"
            "Công việc của bạn là:\n"
            "1. Đọc và hiểu nhiệm vụ.\n"
            "2. Xem xét cẩn thận từng ngữ cảnh được cung cấp.\n"
            "3. Chỉ trích xuất thông tin có liên quan và hữu ích để trả lời nhiệm vụ.\n"
            "4. Loại bỏ bất kỳ nội dung nào rõ ràng không liên quan, dư thừa, hoặc không cung cấp thông tin.\n"
            "5. Đối với ngữ cảnh tìm kiếm trên web, hãy lưu ý rằng chúng có thể chứa thông tin nhiễu hoặc thông tin chung chung — tuy nhiên, đừng loại bỏ chúng hoàn toàn. Xác định và trích xuất bất kỳ phần nào thực sự hữu ích.\n\n" 
            "Đối với mỗi nguồn, hãy trả về:\n"
            "- **URL hoặc Nguồn**\n"
            "- **Ngữ cảnh được trích xuất**: một bản tóm tắt ngắn gọn, liên quan đến nhiệm vụ về thông tin từ nguồn đó.\n\n"
            "Chỉ xuất ra các mục được trích xuất cuối cùng theo định dạng được chỉ định. Không bao gồm giải thích, các bước lập luận hoặc bất kỳ bình luận bổ sung nào."
            "Dưới đây là thông tin được cung cấp:"
            "Nhiệm vụ cần trả lời: {user_input}"
            "Danh sách Ngữ cảnh Đã Truy xuất: {context_text}"
"""
            llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.1)
            response = llm.invoke(extractor_prompt)
            harm_summary = response.content.strip()

            logger.info(
                f"Harm Sub-Agent: generated summary (length={len(harm_summary)} chars)"
            )

            return {
                "harm_results": [{"harm_summary": harm_summary}],
                "nodes_visited": ["harm_agent"],
            }
        else:
            # T039: No context available — return empty results (never return "", LangGraph requires dict)
            logger.warning("Harm Agent: no context found from any tool")
            return {
                "harm_results": [],
                "nodes_visited": ["harm_agent"],
            }

    except Exception as e:
        logger.error(f"Harm Sub-Agent error: {e}", exc_info=True)
        return {
            "harm_results": [],
            "nodes_visited": ["harm_agent"],
            "errors": [f"Harm Sub-Agent error: {str(e)}"],
        }
