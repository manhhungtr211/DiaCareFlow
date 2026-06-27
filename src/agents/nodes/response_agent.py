"""
Response Agent node for the LangGraph pipeline.

Wraps src/rag/qa/generator.py to synthesize a final answer from the
RAG context and writes it to AgentState.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.state import AgentState
from src.rag.qa.data_models import Query, ChunkResult, RetrievedContext
from src.rag.qa.generator import generate

logger = logging.getLogger(__name__)


def response_agent_node(state: AgentState) -> dict[str, Any]:
    """
    Response Agent — generates final answer from RAG context.

    Reads: user_input, rag_context
    Writes: suggestion_context, nodes_visited, error
    """
    logger.info("Response Agent: generating final answer")

    try:
        user_input = state.get("user_input", "")
        rag_context_dicts = state.get("rag_context", [])

        # Reconstruct ChunkResult objects from state dicts
        chunks = [
            ChunkResult(
                content=c.get("content", ""),
                source=c.get("source", "Unknown"),
                score=c.get("score", 0.0),
            )
            for c in rag_context_dicts
        ]

        # Create Query and RetrievedContext for generator
        query = Query(text=user_input)
        context = RetrievedContext(chunks=chunks, query_vector=[])

        # Call existing generator
        answer = generate(query, context)

        logger.info(
            f"Response Agent: generated answer "
            f"(length={len(answer.text)} chars, sources={len(answer.sources)})"
        )

        # Store in suggestion_context dict
        suggestion_context = {
            "final_answer": answer.text,
            "sources": [
                {
                    "content": s.content,
                    "source": s.source,
                    "score": s.score,
                }
                for s in answer.sources
            ],
            "is_refused": answer.is_refused, ### ??? đã truy RAG rồi sao còn từ chối được
            "refuse_reason": answer.refuse_reason, ### kèm luôn
        }

        return {
            "suggestion_context": suggestion_context,
            "nodes_visited": ["response_agent"],
        }

    except Exception as e:
        logger.error(f"Response Agent error: {e}", exc_info=True)
        return {
            "suggestion_context": {
                "final_answer": "Đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại sau.",
                "sources": [],
                "is_refused": False,
                "refuse_reason": None,
            },
            "nodes_visited": ["response_agent"],
            "error": f"Response Agent error: {str(e)}",
        }
