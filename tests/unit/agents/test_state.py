"""
Unit tests for AgentState schema (UC-012).

Verifies:
  - New Annotated fan-in fields exist and are initialized correctly.
  - operator.add reducer appends values correctly (fan-in behavior).
  - Legacy fields are preserved (intent, small_talk_reply, suggestion_context, etc.).
  - Removed fields (rag_context, error) are gone.
"""

from __future__ import annotations

import operator
import pytest
from typing import Annotated, get_type_hints

from src.agents.state import AgentState, SafetyCategory


class TestAgentStateSchema:
    """Validate AgentState field definitions and annotations."""

    def test_new_fan_in_fields_exist(self):
        """UC-012 fan-in fields must exist in AgentState annotations."""
        hints = AgentState.__annotations__
        assert "factor_results" in hints, "factor_results field missing"
        assert "suggestion_results" in hints, "suggestion_results field missing"
        assert "harm_sub_results" in hints, "harm_sub_results field missing"
        assert "errors" in hints, "errors field missing"

    def test_legacy_fields_preserved(self):
        """Fields used before UC-012 (except rag_context) must remain."""
        hints = AgentState.__annotations__
        assert "user_input" in hints
        assert "is_safe" in hints
        assert "harm_task" in hints
        assert "intent" in hints
        assert "small_talk_reply" in hints
        assert "suggestion_context" in hints
        assert "nodes_visited" in hints
        assert "chat_history" in hints
        assert "messageId" in hints

    def test_rag_context_removed(self):
        """rag_context must be removed in UC-012."""
        hints = AgentState.__annotations__
        assert "rag_context" not in hints, "rag_context should have been removed in UC-012"

    def test_error_singular_removed(self):
        """Old singular 'error' field must be replaced by 'errors' list."""
        hints = AgentState.__annotations__
        assert "error" not in hints, "'error' (singular) should be replaced by 'errors' list"

    def test_fan_in_fields_use_annotated_with_operator_add(self):
        """fan-in fields must use Annotated[list[...], operator.add].

        Uses get_type_hints() to resolve ForwardRef strings caused by
        'from __future__ import annotations' (PEP 563, Python 3.13).
        """
        import typing
        hints = typing.get_type_hints(AgentState, include_extras=True)
        for field in ("factor_results", "suggestion_results", "harm_sub_results", "errors"):
            annotation = hints[field]
            # Annotated types have __metadata__ attribute
            assert hasattr(annotation, "__metadata__"), f"{field} must be Annotated"
            assert operator.add in annotation.__metadata__, (
                f"{field} must use operator.add as reducer"
            )

    def test_nodes_visited_uses_operator_add(self):
        """nodes_visited must still use operator.add (unchanged from before UC-012)."""
        import typing
        hints = typing.get_type_hints(AgentState, include_extras=True)
        annotation = hints["nodes_visited"]
        assert hasattr(annotation, "__metadata__")
        assert operator.add in annotation.__metadata__


class TestOperatorAddBehavior:
    """Validate that operator.add correctly merges lists (fan-in behavior)."""

    def test_operator_add_appends_lists(self):
        """operator.add on two lists should concatenate them."""
        a = [{"factor_summary": "Cause A"}]
        b = [{"factor_summary": "Cause B"}]
        result = operator.add(a, b)
        assert len(result) == 2
        assert result[0]["factor_summary"] == "Cause A"
        assert result[1]["factor_summary"] == "Cause B"

    def test_operator_add_empty_lists(self):
        """operator.add on an empty list should return the other list."""
        empty: list = []
        data = [{"suggestion_summary": "Take medicine"}]
        result = operator.add(empty, data)
        assert result == data

    def test_operator_add_strings_for_errors(self):
        """errors field: operator.add should concatenate string lists."""
        err1 = ["factor_agent error: timeout"]
        err2 = ["suggestion_agent error: web down"]
        result = operator.add(err1, err2)
        assert len(result) == 2
        assert "factor_agent error" in result[0]
        assert "suggestion_agent error" in result[1]


class TestSafetyCategoryEnum:
    """Verify SafetyCategory enum is unchanged."""

    def test_all_categories_exist(self):
        assert SafetyCategory.SAFE == "SAFE"
        assert SafetyCategory.PRESCRIPTION == "PRESCRIPTION"
        assert SafetyCategory.DIAGNOSIS == "DIAGNOSIS"
        assert SafetyCategory.EMERGENCY == "EMERGENCY"
