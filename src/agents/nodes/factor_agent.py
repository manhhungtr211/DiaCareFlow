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

_FACTOR_SYSTEM_PROMPT = """Bạn là chuyên gia y khoa chuyên phân tích nguyên nhân và cơ chế bệnh sinh.
Dựa vào tài liệu tham khảo được cung cấp, hãy trả lời ngắn gọn và chính xác:
- Nguyên nhân / cơ chế liên quan đến câu hỏi của người dùng là gì?
- Chỉ trình bày những điểm chính, KHÔNG sáng tạo thêm thông tin ngoài tài liệu.
- Trả lời bằng tiếng Việt, tối đa 3-4 câu."""


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
            prompt = f"""{_FACTOR_SYSTEM_PROMPT}

Tài liệu tham khảo:
{context_text}

Câu hỏi của người dùng: {user_input}

Phân tích nguyên nhân / cơ chế:"""
        else:
            prompt = f"""{_FACTOR_SYSTEM_PROMPT}

Không có tài liệu tham khảo nào được tìm thấy.
Câu hỏi của người dùng: {user_input}

Phân tích nguyên nhân / cơ chế (dựa trên kiến thức y khoa chung):"""

        llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.3)
        response = llm.invoke(prompt)
        factor_summary = response.content.strip()

        logger.info(f"Factor Agent: generated summary (length={len(factor_summary)} chars)")

        return {
            "factor_results": [{"factor_summary": factor_summary, "sources": sources}],
            "nodes_visited": ["factor_agent"],
        }

    except Exception as e:
        logger.error(f"Factor Agent error: {e}", exc_info=True)
        return {
            "factor_results": [],
            "nodes_visited": ["factor_agent"],
            "errors": [f"Factor Agent error: {str(e)}"],
        }
