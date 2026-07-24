"""
Unit tests for harm_agent_node (UC-015).

All external calls (retrieve, web_search, ChatGroq) are mocked.
No network or Qdrant access required.

In the UC-015 flow, the LLM is called TWICE per agent invocation:
  1. Sub-query generation from harm_task (returns list of queries).
  2. Context extraction/summarization (returns harm_summary).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agents.nodes.harm_agent import harm_agent_node


def _make_retrieved(chunks: list):
    r = MagicMock()
    r.chunks = chunks
    return r


def _make_chunk(content="Risk info content", source="guideline.pdf", score=0.9):
    c = MagicMock()
    c.content = content
    c.source = source
    c.score = score
    return c


def _make_web_result(found=True, combined_text="Web risk information"):
    r = MagicMock()
    r.found = found
    r.combined_text = combined_text
    r.scraped_contents = []
    return r


class TestHarmSubAgentHappyPath:
    """harm_agent_node with successful RAG retrieval."""

    @patch("src.agents.nodes.harm_agent.ChatGroq")
    @patch("src.agents.nodes.harm_agent.retrieve")
    def test_rag_success_writes_harm_results(self, mock_retrieve, mock_llm_cls):
        """Should write harm_results with summary when RAG succeeds."""
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Tiêm insulin có nguy hiểm không?"),  # sub-query gen
            MagicMock(content="Cẩn thận với hạ đường huyết"),             # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "Tiêm insulin có nguy hiểm không?", "harm_task": "Tiêm insulin có nguy hiểm không?", "chat_history": []}
        result = harm_agent_node(state)

        assert "harm_results" in result
        assert len(result["harm_results"]) == 1
        assert result["harm_results"][0]["harm_summary"] == "Cẩn thận với hạ đường huyết"
        assert "harm_agent" in result["nodes_visited"]
        assert "errors" not in result
        assert mock_llm.invoke.call_count >= 2  # sub-query gen + extraction

    @patch("src.agents.nodes.harm_agent.ChatGroq")
    @patch("src.agents.nodes.harm_agent.retrieve")
    def test_harm_result_format(self, mock_retrieve, mock_llm_cls):
        """harm_results items must contain harm_summary key."""
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="question"),   # sub-query gen
            MagicMock(content="Risk summary"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "harm_task": "question", "chat_history": []}
        result = harm_agent_node(state)

        item = result["harm_results"][0]
        assert "harm_summary" in item


class TestHarmSubAgentWebFallback:
    """harm_agent_node falls back to web_search when RAG returns no chunks."""

    @patch("src.agents.nodes.harm_agent.ChatGroq")
    @patch("src.agents.nodes.harm_agent.asyncio.run")
    @patch("src.agents.nodes.harm_agent.retrieve")
    def test_web_search_fallback_when_rag_empty(self, mock_retrieve, mock_asyncio_run, mock_llm_cls):
        """When RAG returns 0 chunks, should call web_search and still produce result."""
        mock_retrieve.return_value = _make_retrieved([])
        mock_asyncio_run.return_value = _make_web_result()
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="query"),              # sub-query gen
            MagicMock(content="Web-based risk summary"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "harm_task": "question", "chat_history": []}
        result = harm_agent_node(state)

        mock_asyncio_run.assert_called_once()
        assert result["harm_results"][0]["harm_summary"] == "Web-based risk summary"


class TestHarmSubAgentErrorIsolation:
    """harm_agent_node captures errors into state.errors, never raises."""

    @patch("src.agents.nodes.harm_agent.ChatGroq")
    @patch("src.agents.nodes.harm_agent.retrieve")
    def test_llm_failure_returns_empty_results_and_error(self, mock_retrieve, mock_llm_cls):
        """LLM failure should be caught, errors appended, harm_results=[]."""
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "harm_task": "question", "chat_history": []}
        result = harm_agent_node(state)

        assert result["harm_results"] == []
        assert "errors" in result
        assert "Harm Sub-Agent error" in result["errors"][0]
        assert "harm_agent" in result["nodes_visited"]

    @patch("src.agents.nodes.harm_agent.ChatGroq")
    @patch("src.agents.nodes.harm_agent.asyncio.run")
    @patch("src.agents.nodes.harm_agent.retrieve")
    def test_both_tools_fail_returns_empty_results(self, mock_retrieve, mock_asyncio_run, mock_llm_cls):
        """If both RAG and web fail, no context is available, should return empty results."""
        mock_retrieve.side_effect = ConnectionError("Qdrant down")
        mock_asyncio_run.side_effect = Exception("Web unreachable")
        mock_llm = MagicMock()
        # sub-query generation succeeds
        mock_llm.invoke.return_value = MagicMock(content="question")
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "harm_task": "question", "chat_history": []}
        result = harm_agent_node(state)

        assert len(result["harm_results"]) == 0
        # sub-query gen called once, extraction NOT called (no context)
        assert mock_llm.invoke.call_count == 1
