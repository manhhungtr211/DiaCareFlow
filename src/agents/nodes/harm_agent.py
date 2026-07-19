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

_HARM_SYSTEM_PROMPT = """Bạn là chuyên gia y tế chuyên đánh giá rủi ro và cảnh báo an toàn.
Dựa vào tài liệu tham khảo được cung cấp, hãy trả lời ngắn gọn và cụ thể:
- Những rủi ro, tác dụng phụ, hoặc cảnh báo nào người dùng cần lưu ý?
- Những trường hợp nào cần tham khảo ý kiến bác sĩ ngay?
- KHÔNG sáng tạo thêm thông tin ngoài tài liệu.
- Trả lời bằng tiếng Việt, tối đa 3-4 câu."""


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
            prompt = f"""{_HARM_SYSTEM_PROMPT}

Tài liệu tham khảo:
{context_text}

Câu hỏi của người dùng: {user_input}

Đánh giá rủi ro và cảnh báo an toàn:"""
        else:
            prompt = f"""{_HARM_SYSTEM_PROMPT}

Không có tài liệu tham khảo nào được tìm thấy.
Câu hỏi của người dùng: {user_input}

Đánh giá rủi ro và cảnh báo an toàn (dựa trên kiến thức y khoa chung):"""

        llm = ChatGroq(model_name=GENERATIVE_MODEL, temperature=0.2)
        response = llm.invoke(prompt)
        harm_summary = response.content.strip()

        logger.info(
            f"Harm Sub-Agent: generated summary (length={len(harm_summary)} chars)"
        )

        return {
            "harm_sub_results": [{"harm_summary": harm_summary}],
            "nodes_visited": ["harm_sub_agent"],
        }

    except Exception as e:
        logger.error(f"Harm Sub-Agent error: {e}", exc_info=True)
        return {
            "harm_sub_results": [],
            "nodes_visited": ["harm_sub_agent"],
            "errors": [f"Harm Sub-Agent error: {str(e)}"],
        }
