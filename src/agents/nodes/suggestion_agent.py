"""
Suggestion Agent node for the Multi-Agent pipeline (UC-015).

Generates practical, up-to-date solution suggestions for the user's diabetes-related question.
Flow (per UC-015 spec):
  1. Read suggestion_task from AgentState (set by Supervisor).
  2. Use LLM (_SUGGESTION_SYSTEM_PROMPT) to decompose suggestion_task into ≤2 sub-queries.
  3. For each sub-query:
       a. Primary: web_search() — for current, real-world recommendations.
       b. Fallback: retrieve() (RAG) — when web is unavailable.
  4. Aggregate all context and use LLM to extract a concise suggestion_summary.

Output written to state.suggestion_results (Annotated list, fan-in reducer).
Type contract follows SuggestionOutputState: {"suggestion_summary": str, "sources": list[dict]}.
Errors are captured in state.errors; node never raises.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.state import AgentState, SuggestionState, SuggestionOutputState
from src.config import TOOL_MODEL
from src.tools.rag.qa.data_models import Query
from src.tools.rag.qa.retriever import retrieve
from src.tools.web._api import web_search

logger = logging.getLogger(__name__)

# ── Sub-query Generator Prompt ────────────────────────────────────────────────
_SUGGESTION_SYSTEM_PROMPT = (
    "Bạn là Task Handler của Suggestion Agent. Vai trò của bạn là tạo ra các truy vấn con hiệu quả "
    "giúp truy xuất thông tin chất lượng cao và phù hợp - từ bộ nhớ cục bộ hoặc tìm kiếm trên web - "
    "để hỗ trợ trả lời một nhiệm vụ liên quan đến bệnh tiểu đường.\n\n"
    "Bạn được giao:\n"
    "- Nhiệm vụ: câu hỏi chính cần được trả lời.\n"
    "Công việc của bạn là:\n"
    "1. Hiểu kỹ nhiệm vụ và loại thông tin mà nó có thể cần.\n"
"2. Tạo tối đa 1 *truy vấn con* rõ ràng và tập trung hướng dẫn hệ thống truy xuất thông tin tốt hơn hoặc đầy đủ hơn để hỗ trợ trả lời nhiệm vụ.Sử dụng tiếng Việt. Tạo truy vấn liên quan, không tạo các 'truy vấn 1', 'truy vấn 2', các truy vấn có độ dài dưới 13 từ\n\n"
    "Lưu ý: độ dài các truy vấn con có độ dài dưới 13 từ \n" 
    "Hướng dẫn:\n"
"- Chỉ chia nhỏ hoặc định dạng lại nhiệm vụ nếu làm như vậy sẽ cải thiện hiệu quả truy xuất; Nếu không, hãy tái sử dụng hoặc tinh chỉnh nhẹ nhiệm vụ đó thành một truy vấn con duy nhất.\n"
"Sử dụng tiếng Việt"
)

# ── Extractor Prompt ──────────────────────────────────────────────────────────
_SUGGESTION_EXTRACTOR_TEMPLATE = (
    "Bạn là một Extractor Agent trong hệ thống multi-agent hỗ trợ trả lời các truy vấn liên quan "
    "đến bệnh tiểu đường.\n\n"
    "Nhiệm vụ cần trả lời: {task}\n\n"
    "Danh sách Ngữ cảnh Đã Truy xuất:\n{context_text}\n\n"
    "Công việc của bạn là:\n"
    "1. Đọc và hiểu nhiệm vụ.\n"
    "2. Xem xét cẩn thận từng ngữ cảnh được cung cấp.\n"
    "3. Chỉ trích xuất thông tin có liên quan và hữu ích để trả lời nhiệm vụ — tập trung vào "
    "các đề xuất, giải pháp thực tế, lời khuyên có thể thực hiện được liên quan đến bệnh tiểu đường.\n"
    "4. Loại bỏ bất kỳ nội dung nào rõ ràng không liên quan, dư thừa, hoặc không cung cấp thông tin.\n"
    "5. Đối với ngữ cảnh tìm kiếm trên web, xác định và trích xuất bất kỳ phần nào thực sự hữu ích.\n\n"
    "Đối với mỗi nguồn, hãy trả về:\n"
    "- **URL hoặc Nguồn**\n"
    "- **Ngữ cảnh được trích xuất**: một bản tóm tắt ngắn gọn, liên quan đến nhiệm vụ về thông "
    "tin từ nguồn đó.\n\n"
    "Chỉ xuất ra các mục được trích xuất cuối cùng. Không bao gồm giải thích, các bước lập luận "
    "hoặc bình luận bổ sung."
    "Sử dụng tiếng Việt"

)


import re

def _generate_sub_queries(task: str, llm: ChatGoogleGenerativeAI) -> list[str]:
    """
    Use LLM to decompose suggestion_task into ≤2 focused retrieval sub-queries.
    Returns a list of query strings (never empty — falls back to [task]).
    """
    messages = [
        SystemMessage(content=_SUGGESTION_SYSTEM_PROMPT),
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
        logger.info(f"Suggestion Agent: generated {len(queries)} sub-queries: {queries}")
        return queries
    except Exception as e:
        logger.warning(f"Suggestion Agent: sub-query generation failed ({e}), using task as query")
        return [task]


def _retrieve_context_for_query(query: str) -> tuple[str, list[dict]]:
    """
    Primary: web_search. Fallback: RAG.
    Returns (context_text, sources).
    """
    # Primary: web_search
    try:
        result = asyncio.run(web_search(query))
        if result.found and result.combined_text:
            context_text = result.combined_text[:3000]
            sources = [
                {"content": c.markdown[:500], "source": c.url, "score": 1.0}
                for c in result.scraped_contents
                if c.success
            ]
            logger.info(
                f"Suggestion Agent: web_search returned content "
                f"(length={len(context_text)} chars) for '{query}'"
            )
            return context_text, sources
        else:
            logger.info(f"Suggestion Agent: web_search returned no content for '{query}', trying RAG")
    except Exception as web_err:
        logger.warning(f"Suggestion Agent: web_search failed for '{query}' ({web_err}), trying RAG")

    # Fallback: RAG
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
            logger.info(f"Suggestion Agent: RAG fallback returned {len(retrieved.chunks)} chunks for '{query}'")
            return context_text, sources
    except Exception as rag_err:
        logger.warning(f"Suggestion Agent: RAG fallback also failed for '{query}': {rag_err}")

    return "", []


def suggestion_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Suggestion Agent — provide practical solutions and recommendations.

    Flow (UC-015):
      1. Read suggestion_task from state.
      2. Use LLM to generate ≤2 sub-queries from suggestion_task.
      3. Retrieve context for each sub-query (web_search → RAG fallback).
      4. Aggregate context and run LLM extractor to produce suggestion_summary.

    Reads:  suggestion_task (primary), user_input (fallback)
    Writes: suggestion_results (appended), nodes_visited (appended),
            errors (appended on failure)

    Return type follows SuggestionOutputState contract:
        suggestion_results: [{"suggestion_summary": str, "sources": list[dict]}]
    """
    logger.info("Suggestion Agent: generating practical suggestions")
    task = state.get("suggestion_task") or state.get("user_input", "")
    logger.info(f"Suggestion Agent Input task: {task}")

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
            extractor_prompt = _SUGGESTION_EXTRACTOR_TEMPLATE.format(
                task=task,
                context_text=context_text,
            )
            response = llm.invoke(extractor_prompt)
            suggestion_summary = response.content.strip()

            logger.info(
                f"Suggestion Agent: generated summary (length={len(suggestion_summary)} chars)"
            )

            output = {
                "suggestion_results": [
                    {"suggestion_summary": suggestion_summary, "sources": all_sources}
                ],
                "nodes_visited": ["suggestion_agent"],
            }
        else:
            # No context found from any tool or sub-query
            logger.warning("Suggestion Agent: no context found from any tool")
            output = {
                "suggestion_results": [],
                "nodes_visited": ["suggestion_agent"],
            }

        logger.info(f"Suggestion Agent Output: {output}")
        return output

    except Exception as e:
        logger.error(f"Suggestion Agent error: {e}", exc_info=True)
        output = {
            "suggestion_results": [],
            "nodes_visited": ["suggestion_agent"],
            "errors": [f"Suggestion Agent error: {str(e)}"],
        }
        logger.info(f"Suggestion Agent Output: {output}")
        return output
