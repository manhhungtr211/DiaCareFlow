"""
RAG Agent node for the LangGraph pipeline.

Wraps src/rag/qa/retriever.py to retrieve document chunks from Qdrant
and writes the context to AgentState for the Response Agent.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.state import AgentState
from src.rag.qa.data_models import Query, ChunkResult
from src.rag.qa.retriever import retrieve

logger = logging.getLogger(__name__)


def rag_agent_node(state: AgentState) -> dict[str, Any]:
    """
    RAG Agent — retrieves relevant document chunks for the question.

    Reads: user_input
    Writes: rag_context, nodes_visited, error
    """
    logger.info("RAG Agent: retrieving document context")

    try:
        user_input = state.get("user_input", "")

        # Create Query for retriever
        query = Query(text=user_input)

        # Call existing retriever
        retrieved = retrieve(query, top_k=3) # cần cài đặt biến này ở config

        # Convert chunks to serializable dicts for state
        rag_context = [
            {
                "content": chunk.content,
                "source": chunk.source,
                "score": chunk.score,
            }
            for chunk in retrieved.chunks
        ]

        logger.info(f"RAG Agent: retrieved {len(rag_context)} chunks")

        return {
            "rag_context": rag_context,
            "nodes_visited": ["rag_agent"],
        }

    except ConnectionError as e:
        logger.error(f"RAG Agent: Qdrant connection error: {e}", exc_info=True)
        return {
            "rag_context": [],
            "nodes_visited": ["rag_agent"],
            "error": f"Lỗi kết nối đến Qdrant: {str(e)}",
        }
    except Exception as e:
        logger.error(f"RAG Agent error: {e}", exc_info=True)
        return {
            "rag_context": [],
            "nodes_visited": ["rag_agent"],
            "error": f"RAG Agent error: {str(e)}",
        }
