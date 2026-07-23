"""
Unit tests for DiaCareFlowCallbackHandler (src/agents/tracking/callback_handler.py).

Uses mocking to isolate psutil and LLMResult dependencies.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.outputs import LLMResult

from src.agents.tracking.callback_handler import DiaCareFlowCallbackHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler(session_id: str = "test-session") -> tuple[DiaCareFlowCallbackHandler, list]:
    """Return a handler wired to a list that captures emitted events."""
    handler = DiaCareFlowCallbackHandler(session_id=session_id)
    emitted: list = []
    handler._logger = MagicMock()
    handler._logger.emit.side_effect = lambda ev: emitted.append(ev)
    return handler, emitted


# ---------------------------------------------------------------------------
# Chain (node) callbacks
# ---------------------------------------------------------------------------


class TestChainCallbacks:
    def test_chain_start_records_pending_state(self):
        handler, _ = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        assert str(run_id) in handler._pending
        assert "start_time" in handler._pending[str(run_id)]
        assert "ram_start_mb" in handler._pending[str(run_id)]

    def test_chain_end_emits_event(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        time.sleep(0.01)
        handler.on_chain_end({}, run_id=run_id, name="triage_agent")
        assert len(emitted) == 1
        ev = emitted[0]
        assert ev.event_type == "chain_end"
        assert ev.latency_ms > 0
        assert "start_mb" in ev.ram_usage
        assert "end_mb" in ev.ram_usage
        assert "diff_mb" in ev.ram_usage
        assert ev.session_id == "test-session"

    def test_chain_end_clears_pending(self):
        handler, _ = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_chain_end({}, run_id=run_id, name="supervisor")
        assert str(run_id) not in handler._pending

    def test_chain_error_emits_error_event(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_chain_error(ValueError("boom"), run_id=run_id, name="factor_agent")
        assert len(emitted) == 1
        assert emitted[0].event_type == "chain_error"
        assert "boom" in emitted[0].metadata.get("error", "")

    def test_chain_end_without_start_does_not_crash(self):
        """If on_chain_start was never called, on_chain_end should still not raise."""
        handler, emitted = _make_handler()
        handler.on_chain_end({}, run_id=uuid4(), name="orphan")
        assert len(emitted) == 1  # event still emitted with 0 latency


# ---------------------------------------------------------------------------
# LLM callbacks
# ---------------------------------------------------------------------------


class TestLLMCallbacks:
    def test_llm_end_extracts_token_usage(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_llm_start({}, [], run_id=run_id)

        response = MagicMock(spec=LLMResult)
        response.llm_output = {
            "token_usage": {
                "prompt_tokens": 80,
                "completion_tokens": 40,
                "total_tokens": 120,
            },
            "model_name": "llama3-8b",
        }
        response.generations = []

        handler.on_llm_end(response, run_id=run_id, name="llama3-8b")

        assert len(emitted) == 1
        ev = emitted[0]
        assert ev.event_type == "llm_end"
        assert ev.token_usage["total_tokens"] == 120
        assert ev.token_usage["prompt_tokens"] == 80

    def test_llm_end_captures_input_and_output(self):
        """T013: prompts from on_llm_start and generated text from on_llm_end appear in metadata."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_llm_start({}, ["Tell me about diabetes"], run_id=run_id)

        gen = MagicMock()
        gen.text = "Diabetes is a metabolic disease."
        gen.generation_info = {}

        response = MagicMock(spec=LLMResult)
        response.llm_output = {"model_name": "llama3-8b"}
        response.generations = [[gen]]

        handler.on_llm_end(response, run_id=run_id, name="llama3-8b")

        ev = emitted[0]
        assert "Tell me about diabetes" in ev.metadata["input"][0]
        assert ev.metadata["output"] == "Diabetes is a metabolic disease."

    def test_llm_input_truncated_to_2000_chars(self):
        """T013: prompts longer than 2000 chars must be truncated."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        long_prompt = "x" * 5000
        handler.on_llm_start({}, [long_prompt], run_id=run_id)

        response = MagicMock(spec=LLMResult)
        response.llm_output = {}
        response.generations = []
        handler.on_llm_end(response, run_id=run_id)

        stored = emitted[0].metadata["input"][0]
        assert len(stored) == 2000

    def test_llm_end_handles_missing_token_usage(self):
        """Should not crash if llm_output has no token_usage."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_llm_start({}, [], run_id=run_id)

        response = MagicMock(spec=LLMResult)
        response.llm_output = {}
        response.generations = []

        handler.on_llm_end(response, run_id=run_id)
        assert len(emitted) == 1
        assert emitted[0].token_usage == {}

    def test_llm_error_emits_error_event(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_llm_start({}, [], run_id=run_id)
        handler.on_llm_error(RuntimeError("timeout"), run_id=run_id)
        assert emitted[0].event_type == "llm_error"
        assert "timeout" in emitted[0].metadata.get("error", "")


# ---------------------------------------------------------------------------
# Tool callbacks
# ---------------------------------------------------------------------------


class TestToolCallbacks:
    def test_tool_end_emits_event(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_tool_start({}, "query text", run_id=run_id)
        handler.on_tool_end("search result", run_id=run_id, name="rag_search")
        assert len(emitted) == 1
        assert emitted[0].event_type == "tool_end"
        assert emitted[0].name == "rag_search"

    def test_tool_end_captures_input_and_output(self):
        """T013: tool input_str and output appear in metadata."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_tool_start({}, "blood sugar control", run_id=run_id)
        handler.on_tool_end("Top 5 tips: ...", run_id=run_id, name="rag_search")

        ev = emitted[0]
        assert ev.metadata["input"] == "blood sugar control"
        assert ev.metadata["output"] == "Top 5 tips: ..."

    def test_tool_input_truncated_to_2000_chars(self):
        """T013: tool input longer than 2000 chars must be truncated."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        long_input = "q" * 5000
        handler.on_tool_start({}, long_input, run_id=run_id)
        handler.on_tool_end("ok", run_id=run_id, name="rag_search")

        assert len(emitted[0].metadata["input"]) == 2000

    def test_tool_error_emits_error_event(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_tool_start({}, "query", run_id=run_id)
        handler.on_tool_error(ConnectionError("down"), run_id=run_id, name="rag_search")
        assert emitted[0].event_type == "tool_error"
        assert "down" in emitted[0].metadata.get("error", "")


# ---------------------------------------------------------------------------
# RAM tracking
# ---------------------------------------------------------------------------


class TestRAMTracking:
    def test_ram_usage_fields_present(self):
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_chain_end({}, run_id=run_id, name="aggregate")
        ev = emitted[0]
        for key in ("start_mb", "end_mb", "diff_mb"):
            assert key in ev.ram_usage, f"Missing key: {key}"

    @patch("src.agents.tracking.callback_handler._PSUTIL_AVAILABLE", False)
    def test_ram_tracking_degrades_gracefully_without_psutil(self):
        """When psutil is unavailable, ram_usage should still be a valid dict with 0.0 values."""
        handler, emitted = _make_handler()
        run_id = uuid4()
        handler.on_chain_start({}, {}, run_id=run_id)
        handler.on_chain_end({}, run_id=run_id, name="response_agent")
        ev = emitted[0]
        assert ev.ram_usage["start_mb"] == 0.0
        assert ev.ram_usage["end_mb"] == 0.0
        assert ev.ram_usage["diff_mb"] == 0.0
