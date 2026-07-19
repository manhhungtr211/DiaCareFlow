"""
Suggestion Agent node for the Multi-Agent pipeline (UC-012).

Generates practical, up-to-date solution suggestions for the user's health question.
Tool selection logic:
  - Primary: web_search() — for current, real-world recommendations.
  - Fallback: retrieve() (RAG) — when web is unavailable.

Output written to state.suggestion_results (Annotated list, fan-in reducer).
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

_SUGGESTION_SYSTEM_PROMPT = """Bạn là chuyên gia y tế thực hành, chuyên đưa ra lời khuyên và giải pháp thực tiễn.
Dựa vào tài liệu tham khảo được cung cấp, hãy trả lời ngắn gọn và cụ thể:
- Những giải pháp / lời khuyên thực tế nào phù hợp với câu hỏi của người dùng?
- Ưu tiên thông tin có thể áp dụng ngay trong cuộc sống hàng ngày.
- KHÔNG sáng tạo thêm thông tin ngoài tài liệu.
- Trả lời bằng tiếng Việt, tối đa 3-4 câu."""


def suggestion_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Suggestion Agent — provide practical solutions.

    Tool decision:
      1. Call web_search() first (primary — up-to-date info).
      2. If no web results, fall back to retrieve() (RAG).
      3. Call LLM with the collected context.

    Reads: user_input
    Writes: suggestion_results (appended), nodes_visited (appended), errors (appended on failure)
    """
    logger.info("Suggestion Agent: generating practical suggestions")

    try:
        user_input = state.get("user_input", "")

        # --- Step 1: Try web_search (primary) ---
        context_text = ""
        sources: list[dict] = []

        try:
            result = asyncio.run(web_search(user_input))
            if result.found and result.combined_text:
                context_text = result.combined_text[:3000]  # limit tokens
                sources = [
                    {"content": c.markdown[:500], "source": c.url, "score": 1.0}
                    for c in result.scraped_contents
                    if c.success
                ]
                logger.info(
                    f"Suggestion Agent: web_search returned content "
                    f"(length={len(context_text)} chars)"
                )
        except Exception as web_err:
            logger.warning(
                f"Suggestion Agent: web_search failed ({web_err}), falling back to RAG"
            )

        # --- Step 2: Fallback to RAG if no context yet ---
        if not context_text:
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
                    logger.info(
                        f"Suggestion Agent: RAG fallback returned {len(retrieved.chunks)} chunks"
                    )
            except Exception as rag_err:
                logger.warning(f"Suggestion Agent: RAG fallback also failed: {rag_err}")

        # --- Step 3: LLM summarization ---
        if context_text:
            prompt = f"""{_SUGGESTION_SYSTEM_PROMPT}

Tài liệu tham khảo:
{context_text}

Câu hỏi của người dùng: {user_input}

Đề xuất giải pháp thực tế:"""
        else:
            prompt = f"""{_SUGGESTION_SYSTEM_PROMPT}

Không có tài liệu tham khảo nào được tìm thấy.
Câu hỏi của người dùng: {user_input}

Đề xuất giải pháp thực tế (dựa trên kiến thức y khoa chung):"""

        llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.5)
        response = llm.invoke(prompt)
        suggestion_summary = response.content.strip()

        logger.info(
            f"Suggestion Agent: generated summary (length={len(suggestion_summary)} chars)"
        )

        return {
            "suggestion_results": [
                {"suggestion_summary": suggestion_summary, "sources": sources}
            ],
            "nodes_visited": ["suggestion_agent"],
        }

    except Exception as e:
        logger.error(f"Suggestion Agent error: {e}", exc_info=True)
        return {
            "suggestion_results": [],
            "nodes_visited": ["suggestion_agent"],
            "errors": [f"Suggestion Agent error: {str(e)}"],
        }
