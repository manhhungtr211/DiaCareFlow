"""
Unit tests for suggestion_agent_node (UC-015).

All external calls (web_search, retrieve, ChatGroq) are mocked.
No network or Qdrant access required.

In the UC-015 flow, the LLM is called TWICE per agent invocation:
  1. Sub-query generation from suggestion_task (LLM.invoke returns list of queries).
  2. Context extraction/summarization (LLM.invoke returns suggestion_summary).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agents.nodes.suggestion_agent import suggestion_agent_node


def _make_web_result(found=True, combined_text="Practical web suggestions"):
    r = MagicMock()
    r.found = found
    r.combined_text = combined_text
    scraped = MagicMock()
    scraped.success = True
    scraped.markdown = "Web markdown"
    scraped.url = "https://example.com"
    r.scraped_contents = [scraped]
    return r


def _make_retrieved(chunks: list):
    r = MagicMock()
    r.chunks = chunks
    return r


def _make_chunk(content="RAG content", source="doc.pdf", score=0.8):
    c = MagicMock()
    c.content = content
    c.source = source
    c.score = score
    return c


class TestSuggestionAgentHappyPath:
    """suggestion_agent_node with successful web_search."""

    @patch("src.agents.nodes.suggestion_agent.ChatGroq")
    @patch("src.agents.nodes.suggestion_agent.asyncio.run")
    def test_web_search_success_writes_suggestion_results(self, mock_asyncio_run, mock_llm_cls):
        """Should write suggestion_results with summary when web_search succeeds."""
        mock_asyncio_run.return_value = _make_web_result()
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Tiền tiểu đường nên ăn gì?"),             # sub-query gen
            MagicMock(content="Nên ăn rau xanh và ngũ cốc nguyên hạt"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "Tiền tiểu đường nên ăn gì?", "suggestion_task": "Tiền tiểu đường nên ăn gì?", "chat_history": []}
        result = suggestion_agent_node(state)

        assert "suggestion_results" in result
        assert len(result["suggestion_results"]) == 1
        assert result["suggestion_results"][0]["suggestion_summary"] == "Nên ăn rau xanh và ngũ cốc nguyên hạt"
        assert "suggestion_agent" in result["nodes_visited"]
        assert "errors" not in result
        assert mock_llm.invoke.call_count >= 2  # sub-query gen + extraction

    @patch("src.agents.nodes.suggestion_agent.ChatGroq")
    @patch("src.agents.nodes.suggestion_agent.asyncio.run")
    def test_suggestion_results_include_web_sources(self, mock_asyncio_run, mock_llm_cls):
        """suggestion_results sources should come from scraped web content."""
        mock_asyncio_run.return_value = _make_web_result()
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="question"),  # sub-query gen
            MagicMock(content="Summary"),   # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "suggestion_task": "question", "chat_history": []}
        result = suggestion_agent_node(state)

        sources = result["suggestion_results"][0]["sources"]
        assert len(sources) >= 1
        assert sources[0]["source"] == "https://example.com"


class TestSuggestionAgentRagFallback:
    """suggestion_agent_node falls back to RAG when web_search fails."""

    @patch("src.agents.nodes.suggestion_agent.ChatGroq")
    @patch("src.agents.nodes.suggestion_agent.retrieve")
    @patch("src.agents.nodes.suggestion_agent.asyncio.run")
    def test_rag_fallback_when_web_fails(self, mock_asyncio_run, mock_retrieve, mock_llm_cls):
        """When web_search fails, should fall back to RAG and still produce a result."""
        mock_asyncio_run.side_effect = Exception("Network error")
        mock_retrieve.return_value = _make_retrieved([_make_chunk()])
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="question"),          # sub-query gen
            MagicMock(content="RAG-based suggestion"),  # extraction
        ]
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "suggestion_task": "question", "chat_history": []}
        result = suggestion_agent_node(state)

        mock_retrieve.assert_called_once()
        assert result["suggestion_results"][0]["suggestion_summary"] == "RAG-based suggestion"


class TestSuggestionAgentErrorIsolation:
    """suggestion_agent_node captures LLM errors into state.errors."""

    @patch("src.agents.nodes.suggestion_agent.ChatGroq")
    @patch("src.agents.nodes.suggestion_agent.asyncio.run")
    def test_llm_failure_returns_empty_results_and_error(self, mock_asyncio_run, mock_llm_cls):
        """LLM failure should be caught, errors appended, suggestion_results=[]."""
        mock_asyncio_run.return_value = _make_web_result()
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM quota exceeded")
        mock_llm_cls.return_value = mock_llm

        state = {"user_input": "question", "suggestion_task": "question", "chat_history": []}
        result = suggestion_agent_node(state)

        assert result["suggestion_results"] == []
        assert "errors" in result
        assert "Suggestion Agent error" in result["errors"][0]
        assert "suggestion_agent" in result["nodes_visited"]
