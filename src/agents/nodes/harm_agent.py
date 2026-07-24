"""
Harm Sub-Agent node for the Multi-Agent pipeline (UC-015).

Evaluates health risks, contraindications, and safety warnings related to
the user's diabetes-related question.
Flow (per UC-015 spec):
  1. Read harm_task from AgentState (set by Supervisor).
  2. Use LLM (_HARM_SYSTEM_PROMPT) to decompose harm_task into ≤2 sub-queries.
  3. For each sub-query:
       a. Primary: retrieve() (RAG) — medical guidelines and safety data.
       b. Fallback: web_search() — when RAG returns no chunks.
  4. Aggregate all context and use LLM to extract a concise harm_summary.

Output written to state.harm_results (Annotated list, fan-in reducer).
Type contract follows HarmOutputState: {"harm_summary": str}.
Errors are captured in state.errors; node never raises.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState, HarmState, HarmOutputState
from src.config import TOOL_MODEL
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
_HARM_SYSTEM_PROMPT = """Bạn là Task Handler của Harm Agent. Vai trò của bạn là tạo ra các truy vấn con hiệu quả giúp truy xuất
thông tin chất lượng cao và phù hợp - từ bộ nhớ cục bộ hoặc tìm kiếm trên web - để hỗ trợ trả lời một nhiệm vụ liên quan đến bệnh tiểu đường.

Bạn được giao:
- Nhiệm vụ: câu hỏi chính cần được trả lời.

Công việc của bạn là:
1. Hiểu kỹ nhiệm vụ và loại thông tin mà nó có thể cần.
2. Tạo tối đa 1 *truy vấn con* rõ ràng và tập trung hướng dẫn hệ. các truy vấn có độ dài dưới 13 từ.
    Lưu ý: độ dài các truy vấn con có độ dài dưới 13 từ
Hướng dẫn:
- Chỉ chia nhỏ hoặc định dạng lại nhiệm vụ nếu làm như vậy sẽ cải thiện hiệu quả truy xuất; Nếu không, hãy tái sử dụng hoặc tinh chỉnh nhẹ nhiệm vụ đó thành một truy vấn con duy nhất.
- Mỗi truy vấn con phải cụ thể, không trùng lặp và trực tiếp nhằm mục đích làm phong phú thêm thông tin cần thiết cho nhiệm vụ.

Sử dụng tiếng Việt
"""
# ── Extractor Prompt ──────────────────────────────────────────────────────────
_HARM_EXTRACTOR_TEMPLATE = (
    "Bạn là một Extractor Agent trong hệ thống multi-agent hỗ trợ trả lời các truy vấn liên quan "
    "đến bệnh tiểu đường.\n\n"
    "Nhiệm vụ cần trả lời: {task}\n\n"
    "Danh sách Ngữ cảnh Đã Truy xuất:\n{context_text}\n\n"
    "Công việc của bạn là:\n"
    "1. Đọc và hiểu nhiệm vụ.\n"
    "2. Xem xét cẩn thận từng ngữ cảnh được cung cấp.\n"
    "3. Chỉ trích xuất thông tin có liên quan và hữu ích để trả lời nhiệm vụ — tập trung vào "
    "rủi ro, tác hại, tác dụng phụ và cảnh báo an toàn liên quan đến bệnh tiểu đường.\n"
    "4. Loại bỏ bất kỳ nội dung nào rõ ràng không liên quan, dư thừa, hoặc không cung cấp thông tin.\n"
    "5. Đối với ngữ cảnh tìm kiếm trên web, xác định và trích xuất bất kỳ phần nào thực sự hữu ích.\n\n"
    "Đối với mỗi nguồn, hãy trả về:\n"
    "- **URL hoặc Nguồn**\n"
    "- **Ngữ cảnh được trích xuất**: một bản tóm tắt ngắn gọn, liên quan đến nhiệm vụ về thông "
    "tin từ nguồn đó.\n\n"
    "Chỉ xuất ra các mục được trích xuất cuối cùng. Không bao gồm giải thích, các bước lập luận "
    "hoặc bình luận bổ sung."
)


import re

def _generate_sub_queries(task: str, llm: ChatGoogleGenerativeAI) -> list[str]:
    """
    Use LLM to decompose harm_task into ≤2 focused retrieval sub-queries.
    Returns a list of query strings (never empty — falls back to [task]).
    """
    messages = [
        SystemMessage(content=_HARM_SYSTEM_PROMPT),
        HumanMessage(content=f"Nhiệm vụ: {task}"),
    ]
    try:
        response = llm.invoke(messages)
        lines = [line.strip() for line in response.content.strip().splitlines() if line.strip()]
        
        cleaned_queries = []
        for line in lines:
            clean_line = line.strip()
            # Remove bold formatting
            clean_line = clean_line.replace("**", "")
            # Skip lines that are just "Sub-query 1" or "Truy vấn 1" (with or without colon)
            if re.match(r'^(?:Sub[-\s\u2011-\u2015]?query|Truy vấn(?: con)?)\s*\d*\s*:?$', clean_line, flags=re.IGNORECASE):
                continue
            
            # Remove common LLM prefixes like "Sub-query 1:" or "Truy vấn con 1:"
            clean_line = re.sub(r'^(?:Sub[-\s\u2011-\u2015]?query|Truy vấn(?: con)?)\s*\d*\s*:\s*', '', clean_line, flags=re.IGNORECASE)
            
            # Remove leading bullets or numbers
            clean_line = re.sub(r'^(\d+\.|[-*•])\s*', '', clean_line).strip()
            # Remove surrounding quotes if present (including curly quotes)
            clean_line = clean_line.strip('"\'“”‘’')
            if clean_line:
                cleaned_queries.append(clean_line)
                
        queries = cleaned_queries[:2] if cleaned_queries else [task]
        logger.info(f"Harm Agent: generated {len(queries)} sub-queries: {queries}")
        return queries
    except Exception as e:
        logger.warning(f"Harm Agent: sub-query generation failed ({e}), using task as query")
        return [task]


def _retrieve_context_for_query(query: str) -> tuple[str, list[dict]]:
    """
    Primary: RAG. Fallback: web_search.
    Returns (context_text, sources).
    """
    # Primary: RAG
    try:
        q = Query(text=query)
        retrieved = retrieve(q)
        if retrieved.chunks:
            context_text = "\n\n".join(
                f"[Nguồn: {c.source}]\n{c.content}" for c in retrieved.chunks
            )
            sources = [
                {"content": c.content, "source": c.source, "score": c.score}
                for c in retrieved.chunks
            ]
            logger.info(f"Harm Agent: RAG returned {len(retrieved.chunks)} chunks for '{query}'")
            return context_text, sources
        else:
            logger.info(f"Harm Agent: RAG returned 0 chunks for '{query}', trying web_search")
    except Exception as rag_err:
        logger.warning(f"Harm Agent: RAG failed for '{query}' ({rag_err}), trying web_search")

    # Fallback: web_search
    try:
        result = asyncio.run(web_search(query))
        if result.found and result.combined_text:
            context_text = result.combined_text[:3000]
            logger.info(f"Harm Agent: web_search fallback succeeded for '{query}'")
            return context_text, []
    except Exception as web_err:
        logger.warning(f"Harm Agent: web_search fallback also failed for '{query}': {web_err}")

    return "", []


def harm_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Harm Sub-Agent — assess health risks and safety warnings.

    Flow (UC-015):
      1. Read harm_task from state.
      2. Use LLM to generate ≤2 sub-queries from harm_task.
      3. Retrieve context for each sub-query (RAG → web_search fallback).
      4. Aggregate context and run LLM extractor to produce harm_summary.

    Reads:  harm_task (primary), user_input (fallback)
    Writes: harm_results (appended), nodes_visited (appended),
            errors (appended on failure)

    Return type follows HarmOutputState contract:
        harm_results: [{"harm_summary": str}]
    """
    logger.info("Harm Sub-Agent: assessing health risks")
    task = state.get("harm_task") or state.get("user_input", "")
    logger.info(f"Harm Sub-Agent Input task: {task}")

    try:
        llm = ChatGoogleGenerativeAI(model=TOOL_MODEL, temperature=0.1)

        # --- Step 1: Generate sub-queries via LLM ---
        sub_queries = _generate_sub_queries(task, llm)

        # --- Step 2+3: Retrieve context for each sub-query ---
        all_context_parts: list[str] = []

        for query in sub_queries:
            ctx, _ = _retrieve_context_for_query(query)
            if ctx:
                all_context_parts.append(ctx)

        context_text = "\n\n---\n\n".join(all_context_parts)

        # --- Step 4: LLM extraction ---
        if context_text:
            extractor_prompt = _HARM_EXTRACTOR_TEMPLATE.format(
                task=task,
                context_text=context_text,
            )
            response = llm.invoke(extractor_prompt)
            harm_summary = response.content.strip()

            logger.info(
                f"Harm Sub-Agent: generated summary (length={len(harm_summary)} chars)"
            )

            output = {
                "harm_results": [{"harm_summary": harm_summary}],
                "nodes_visited": ["harm_agent"],
            }
        else:
            # No context found from any tool or sub-query
            logger.warning("Harm Agent: no context found from any tool")
            output = {
                "harm_results": [],
                "nodes_visited": ["harm_agent"],
            }

        logger.info(f"Harm Sub-Agent Output: {output}")
        return output

    except Exception as e:
        logger.error(f"Harm Sub-Agent error: {e}", exc_info=True)
        output = {
            "harm_results": [],
            "nodes_visited": ["harm_agent"],
            "errors": [f"Harm Sub-Agent error: {str(e)}"],
        }
        logger.info(f"Harm Sub-Agent Output: {output}")
        return output
