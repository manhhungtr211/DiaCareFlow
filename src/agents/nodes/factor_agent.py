"""
Factor Agent node for the Multi-Agent pipeline (UC-015).

Analyzes root causes and contributing factors for the user's diabetes-related question.
Flow (per UC-015 spec):
  1. Read factor_task from AgentState (set by Supervisor).
  2. Use LLM (_FACTOR_SYSTEM_PROMPT) to decompose factor_task into ≤2 sub-queries.
  3. For each sub-query:
       a. Primary: retrieve() (RAG) — medical guidelines and deep medical knowledge.
       b. Fallback: web_search() — when RAG returns no chunks.
  4. Aggregate all context and use LLM to extract a concise factor_summary.

Output written to state.factor_results (Annotated list, fan-in reducer).
Type contract follows FactorOutputState: {"factor_summary": str, "sources": list[dict]}.
Errors are captured in state.errors; node never raises.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState, FactorState, FactorOutputState
from src.config import TOOL_MODEL
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
"thông tin chất lượng cao và phù hợp - từ bộ nhớ cục bộ hoặc tìm kiếm trên web - để hỗ trợ trả lời một nhiệm vụ liên quan đến bệnh tiểu đường.\n\n"
    "Bạn được giao:\n"
    "- Nhiệm vụ: câu hỏi chính cần được trả lời.\n"
    "Công việc của bạn là:\n"
    "1. Hiểu kỹ nhiệm vụ và loại thông tin mà nó có thể cần.\n"
    "2. Tạo tối đa 1 truy vấn rõ ràng và tập trung hướng dẫn hệ thống truy xuất thông tin tốt hơn hoặc đầy đủ hơn để hỗ trợ trả lời nhiệm vụ. Tạo truy vấn liên quan, không tạo các 'truy vấn 1', 'truy vấn 2'.\n\n"
    Lưu ý: độ dài các truy vấn có độ dài dưới 13 từ
    "Hướng dẫn:\n"
    "- Chỉ chia nhỏ hoặc định dạng lại nhiệm vụ nếu làm như vậy sẽ cải thiện hiệu quả truy xuất; Nếu không, hãy tái sử dụng hoặc tinh chỉnh nhẹ nhiệm vụ đó thành một truy vấn duy nhất.\n"
    "- Mỗi truy vấn phải cụ thể, không trùng lặp và trực tiếp nhằm mục đích làm phong phú thêm thông tin cần thiết cho nhiệm vụ.\n"
Sử dụng tiếng Việt

"""

import re

def _generate_sub_queries(task: str, llm: ChatGoogleGenerativeAI) -> list[str]:
    """
    Use LLM to decompose factor_task into ≤2 focused retrieval sub-queries.
    Returns a list of query strings (never empty — falls back to [task]).
    """
    messages = [
        SystemMessage(content=_FACTOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Nhiệm vụ: {task}"),
    ]
    try:
        response = llm.invoke(messages)
        lines = [line.strip() for line in response.content.strip().splitlines() if line.strip()]
        
        cleaned_queries = []
        for line in lines:
            # Remove bold formatting
            clean_line = line.replace("**", "").strip()
            # Remove common LLM prefixes like "Sub-query 1:" or "Truy vấn con 1:"
            clean_line = re.sub(r'^(?:Sub-query|Truy vấn(?: con)?)\s*\d*\s*:\s*', '', clean_line, flags=re.IGNORECASE)
            # Remove leading bullets or numbers
            clean_line = re.sub(r'^(\d+\.|[-*•])\s*', '', clean_line).strip()
            # Remove surrounding quotes if present (including curly quotes)
            clean_line = clean_line.strip('"\'“”‘’')
            if clean_line:
                cleaned_queries.append(clean_line)
                
        queries = cleaned_queries[:2] if cleaned_queries else [task]
        logger.info(f"Factor Agent: generated {len(queries)} sub-queries: {queries}")
        return queries
    except Exception as e:
        logger.warning(f"Factor Agent: sub-query generation failed ({e}), using task as query")
        return [task]


def _retrieve_context_for_query(query: str) -> tuple[str, list[dict]]:
    """
    Try RAG first, fall back to web_search.
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
            logger.info(f"Factor Agent: RAG returned {len(retrieved.chunks)} chunks for '{query}'")
            return context_text, sources
        else:
            logger.info(f"Factor Agent: RAG returned 0 chunks for '{query}', trying web_search")
    except Exception as rag_err:
        logger.warning(f"Factor Agent: RAG failed for '{query}' ({rag_err}), trying web_search")

    # Fallback: web_search
    try:
        result = asyncio.run(web_search(query))
        if result.found and result.combined_text:
            context_text = result.combined_text[:3000]
            logger.info(f"Factor Agent: web_search fallback succeeded for '{query}'")
            return context_text, []
    except Exception as web_err:
        logger.warning(f"Factor Agent: web_search fallback also failed for '{query}': {web_err}")

    return "", []


def factor_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Factor Agent — analyze root causes and contributing factors.

    Flow (UC-015):
      1. Read factor_task from state.
      2. Use LLM to generate ≤2 sub-queries from factor_task.
      3. Retrieve context for each sub-query (RAG → web_search fallback).
      4. Aggregate context and run LLM extractor to produce factor_summary.

    Reads:  factor_task (primary), user_input (fallback)
    Writes: factor_results (appended), nodes_visited (appended),
            errors (appended on failure)

    Return type follows FactorOutputState contract:
        factor_results: [{"factor_summary": str, "sources": list[dict]}]
    """
    logger.info("Factor Agent: analyzing root causes")
    task = state.get("factor_task") or state.get("user_input", "")
    logger.info(f"Factor Agent Input task: {task}")

    try:
        llm = ChatGoogleGenerativeAI(model=TOOL_MODEL, temperature=0.1)

        # --- Step 1: Generate sub-queries via LLM ---
        sub_queries = _generate_sub_queries(task, llm)

        # --- Step 2+3: Retrieve context for each sub-query ---
        all_context_parts: list[str] = []
        all_sources: list[dict] = []

        for query in sub_queries:
            ctx, srcs = _retrieve_context_for_query(query)
            if ctx:
                all_context_parts.append(ctx)
                all_sources.extend(srcs)

        context_text = "\n\n---\n\n".join(all_context_parts)

        # --- Step 4: LLM extraction ---
        if context_text:
            extractor_prompt = f"""Bạn là một Extractor Agent trong hệ thống multi-agent hỗ trợ trả lời các truy vấn liên quan đến bệnh tiểu đường.

Nhiệm vụ cần trả lời: {task}

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
            llm = ChatGoogleGenerativeAI(model=TOOL_MODEL, temperature=0.1)
            response = llm.invoke(extractor_prompt)
            factor_summary = response.content.strip()

            logger.info(
                f"Factor Agent: generated summary (length={len(factor_summary)} chars)"
            )

            output = {
                "factor_results": [{"factor_summary": factor_summary, "sources": all_sources}],
                "nodes_visited": ["factor_agent"],
            }
        else:
            # No context found from any tool or sub-query
            logger.warning("Factor Agent: no context found from any tool")
            output = {
                "factor_results": [],
                "nodes_visited": ["factor_agent"],
            }

        logger.info(f"Factor Agent Output: {output}")
        return output

    except Exception as e:
        logger.error(f"Factor Agent error: {e}", exc_info=True)
        output = {
            "factor_results": [],
            "nodes_visited": ["factor_agent"],
            "errors": [f"Factor Agent error: {str(e)}"],
        }
        logger.info(f"Factor Agent Output: {output}")
        return output
