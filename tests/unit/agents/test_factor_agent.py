"""
Unit tests for factor_agent_node (UC-015).

All external calls (retrieve, web_search, ChatGroq) are mocked.
No network or Qdrant access required.

In the UC-015 flow, the LLM is called TWICE per agent invocation:
  1. Sub-query generation from *_task (returns list of queries).
  2. Context extraction/summarization (returns factor_summary).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.agents.nodes.factor_agent import factor_agent_node


def _make_retrieved(chunks: list):
    r = MagicMock()
    r.chunks = chunks
    return r


def _make_chunk(content="Medical content", source="doc.pdf", score=0.9):
    c = MagicMock()
    c.content = content
    c.source = source
    c.score = score
    return c


def _make_web_result(found=True, combined_text="Web content about causes"):
    r = MagicMock()
    r.found = found
    r.combined_text = combined_text
    r.scraped_contents = []
    return r


class TestFactorAgentHappyPath:
    """factor_agent_node with successful RAG retrieval."""

    @patch("src.agents.nodes.factor_agent.ChatGroq")
    @patch("src.agents.nodes.factor_agent.retrieve")
    def test_rag_success_writes_factor_results(self, mock_retrieve, mock_llm_cls):
        """Should write factor_results with summary and sources when RAG succeeds."""
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        # First call: sub-query generation (returns one query line)
        # Second call: extraction (returns the summary)
        mock_llm.invoke.side_effect = [
            MagicMock(content="Tại sao bị tiểu đường?"),  # sub-query
            MagicMock(content="Nguyên nhân: do tiểu đường type 2"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "Tại sao bị tiểu đường?", "factor_task": "Tại sao bị tiểu đường?", "chat_history": []}
        result = factor_agent_node(state)

        assert "factor_results" in result
        assert len(result["factor_results"]) == 1
        assert "factor_summary" in result["factor_results"][0]
        assert result["factor_results"][0]["factor_summary"] == "Nguyên nhân: do tiểu đường type 2"
        assert "nodes_visited" in result
        assert "factor_agent" in result["nodes_visited"]
        assert "errors" not in result  # no errors on happy path
        # LLM must be called at least twice: sub-query gen + extraction
        assert mock_llm.invoke.call_count >= 2

    @patch("src.agents.nodes.factor_agent.ChatGroq")
    @patch("src.agents.nodes.factor_agent.retrieve")
    def test_factor_results_include_sources(self, mock_retrieve, mock_llm_cls):
        """factor_results should contain sources list from RAG."""
        chunk = _make_chunk(content="RAG content", source="source.pdf", score=0.8)
        mock_retrieve.return_value = _make_retrieved([chunk])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="question"),  # sub-query gen
            MagicMock(content="Summary"),   # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "factor_task": "question", "chat_history": []}
        result = factor_agent_node(state)

        sources = result["factor_results"][0]["sources"]
        assert len(sources) == 1
        assert sources[0]["source"] == "source.pdf"


class TestFactorAgentRagFallback:
    """factor_agent_node falls back to web_search when RAG returns no chunks."""

    @patch("src.agents.nodes.factor_agent.ChatGroq")
    @patch("src.agents.nodes.factor_agent.asyncio.run")
    @patch("src.agents.nodes.factor_agent.retrieve")
    def test_web_search_fallback_when_rag_empty(self, mock_retrieve, mock_asyncio_run, mock_llm_cls):
        """When RAG returns 0 chunks, should call web_search and still produce result."""
        mock_retrieve.return_value = _make_retrieved([])  # no chunks
        mock_asyncio_run.return_value = _make_web_result()
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="query"),         # sub-query gen
            MagicMock(content="Web-based summary"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "factor_task": "question", "chat_history": []}
        result = factor_agent_node(state)

        mock_asyncio_run.assert_called_once()
        assert result["factor_results"][0]["factor_summary"] == "Web-based summary"


class TestFactorAgentErrorIsolation:
    """factor_agent_node captures errors into state.errors, never raises."""

    @patch("src.agents.nodes.factor_agent.ChatGroq")
    @patch("src.agents.nodes.factor_agent.asyncio.run")
    @patch("src.agents.nodes.factor_agent.retrieve")
    def test_rag_and_web_both_fail_returns_empty_factor_results(
        self, mock_retrieve, mock_asyncio_run, mock_llm_cls
    ):
        """If both RAG and web_search fail, should return empty factor_results.

        In UC-015 flow, the sub-query LLM call succeeds (returns fallback to task),
        but retrieval from both sources fails → no context → empty results.
        """
        mock_retrieve.side_effect = ConnectionError("Qdrant down")
        mock_asyncio_run.side_effect = Exception("Web unreachable")
        mock_llm = MagicMock()
        # sub-query generation succeeds (returns the task as-is)
        mock_llm.invoke.return_value = MagicMock(content="question")
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "factor_task": "question", "chat_history": []}
        result = factor_agent_node(state)

        # Should return empty result without calling extraction LLM
        assert len(result["factor_results"]) == 0
        # sub-query gen is called once, extraction is NOT called (no context)
        assert mock_llm.invoke.call_count == 1

    @patch("src.agents.nodes.factor_agent.ChatGroq")
    @patch("src.agents.nodes.factor_agent.retrieve")
    def test_llm_failure_returns_empty_results_and_error(self, mock_retrieve, mock_llm_cls):
        """LLM failure should be caught, errors appended, factor_results=[]. """
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM timeout")
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "factor_task": "question", "chat_history": []}
        result = factor_agent_node(state)

        assert result["factor_results"] == []
        assert "errors" in result
        assert len(result["errors"]) == 1
        assert "Factor Agent error" in result["errors"][0]
        assert "factor_agent" in result["nodes_visited"]
