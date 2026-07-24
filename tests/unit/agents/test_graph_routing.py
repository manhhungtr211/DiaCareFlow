"""
Unit tests for graph routing logic (UC-012).

Tests T019 (US1 happy path routing) and T020-T023 (US2 unsafe + SMALL_TALK routing).

All node functions are mocked — no LLM, RAG, or web calls.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agents.graph import _route_after_triage, _dispatch_sub_agents
from src.agents.state import AgentState, SafetyCategory


# ---------------------------------------------------------------------------
# Helper: build minimal AgentState-like dict
# ---------------------------------------------------------------------------


def _make_state(
    is_safe: bool = True,
    intent: str = "DIABETES",
    user_input: str = "Người tiền tiểu đường nên ăn gì?",
    harm_task: str = "",
    should_response: bool = False,
    follow_up_question: str = "",
    nodes_visited: list | None = None,
    factor_results: list | None = None,
    suggestion_results: list | None = None,
    harm_results: list | None = None,
    errors: list | None = None,
) -> dict:
    return {
        "user_input": user_input,
        "is_safe": is_safe,
        "intent": intent,
        "harm_task": harm_task,
        "should_response": should_response,
        "follow_up_question": follow_up_question,
        "nodes_visited": nodes_visited or [],
        "factor_results": factor_results or [],
        "suggestion_results": suggestion_results or [],
        "harm_results": harm_results or [],
        "errors": errors or [],
        "chat_history": [],
        "small_talk_reply": "",
    }


# ---------------------------------------------------------------------------
# T019: US1 — Happy Path Routing
# ---------------------------------------------------------------------------


class TestHappyPathRouting:
    """T019: verify routing for safe DIABETES question."""

    def test_triage_safe_routes_to_supervisor(self):
        """is_safe=True should route triage_agent → supervisor."""
        state = _make_state(is_safe=True)
        result = _route_after_triage(state)
        assert result == "supervisor"

    def test_supervisor_diabetes_dispatches_send(self):
        """intent=DIABETES (and should_response=False) should fan-out to 3 sub-agents."""
        from langgraph.types import Send
        state = _make_state(is_safe=True, intent="DIABETES")
        result = _dispatch_sub_agents(state)
        assert isinstance(result, list), "Should return list of Send objects for DIABETES"
        assert len(result) == 3
        node_names = [s.node for s in result]
        assert "factor_agent" in node_names
        assert "suggestion_agent" in node_names
        assert "harm_agent" in node_names

    def test_send_objects_carry_user_input(self):
        """Send objects must carry user_input so sub-agents can read it."""
        from langgraph.types import Send
        state = _make_state(is_safe=True, intent="DIABETES", user_input="test question")
        sends = _dispatch_sub_agents(state)
        for send in sends:
            assert send.arg.get("user_input") == "test question", (
                f"Send to {send.node} missing user_input"
            )


# ---------------------------------------------------------------------------
# T020/T021: US2 — Unsafe path routing
# ---------------------------------------------------------------------------


class TestUnsafePathRouting:
    """T020: verify unsafe question bypasses supervisor and sub-agents."""

    def test_triage_unsafe_routes_directly_to_response_agent(self):
        """is_safe=False should route triage_agent → response_agent (skip supervisor)."""
        state = _make_state(is_safe=False)
        result = _route_after_triage(state)
        assert result == "response_agent", (
            "Unsafe questions must go directly to response_agent, skipping all sub-agents"
        )

    def test_unsafe_never_reaches_supervisor(self):
        """_route_after_triage with is_safe=False must NOT return 'supervisor'."""
        state = _make_state(is_safe=False)
        result = _route_after_triage(state)
        assert result != "supervisor"

    def test_unsafe_never_reaches_sub_agents(self):
        """_route_after_triage with is_safe=False must NOT return any sub-agent name."""
        state = _make_state(is_safe=False)
        result = _route_after_triage(state)
        assert result not in ("factor_agent", "suggestion_agent", "harm_agent")


# ---------------------------------------------------------------------------
# T022/T023: US2 — SMALL_TALK bypass
# ---------------------------------------------------------------------------


class TestSmallTalkRouting:
    """T023: verify SMALL_TALK intent (via should_response=True) bypasses sub-agents."""

    def test_smalltalk_routes_to_response_agent_not_sub_agents(self):
        """should_response=True should route supervisor → response_agent directly."""
        state = _make_state(is_safe=True, intent="SMALL_TALK", should_response=True)
        result = _dispatch_sub_agents(state)
        assert result == "response_agent", (
            "SMALL_TALK must bypass all sub-agents and go directly to response_agent"
        )

    def test_smalltalk_does_not_return_send_list(self):
        """SMALL_TALK (should_response=True) must not fan-out (no Send objects)."""
        from langgraph.types import Send
        state = _make_state(is_safe=True, intent="SMALL_TALK", should_response=True)
        result = _dispatch_sub_agents(state)
        assert not isinstance(result, list), "SMALL_TALK should not produce Send fan-out"

    def test_diabetes_is_not_small_talk(self):
        """intent=DIABETES must never route to response_agent directly from supervisor."""
        from langgraph.types import Send
        state = _make_state(is_safe=True, intent="DIABETES")
        result = _dispatch_sub_agents(state)
        assert isinstance(result, list), "DIABETES should fan-out to 3 sub-agents"
        assert result != "response_agent"
