"""
Unit tests for the LogEvent dataclass (src/agents/tracking/models.py).
"""

import json
import pytest
from src.agents.tracking.models import LogEvent


class TestLogEvent:
    """Tests for LogEvent dataclass construction and serialisation."""

    def test_default_values(self):
        """LogEvent should be constructable with no arguments and have sensible defaults."""
        event = LogEvent()
        assert isinstance(event.event_id, str)
        assert len(event.event_id) == 36  # UUID4 format: 8-4-4-4-12
        assert event.session_id == ""
        assert event.event_type == ""
        assert event.name == ""
        assert event.start_time == 0.0
        assert event.end_time == 0.0
        assert event.latency_ms == 0.0
        assert event.token_usage == {}
        assert event.ram_usage == {}
        assert event.metadata == {}

    def test_unique_event_ids(self):
        """Each LogEvent should get a unique event_id."""
        ids = {LogEvent().event_id for _ in range(50)}
        assert len(ids) == 50

    def test_field_assignment(self):
        """Fields set at construction should be preserved exactly."""
        event = LogEvent(
            session_id="abc-123",
            event_type="chain_end",
            name="triage_agent",
            start_time=1_700_000_000.0,
            end_time=1_700_000_001.2,
            latency_ms=1200.0,
            token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            ram_usage={"start_mb": 310.0, "end_mb": 312.5, "diff_mb": 2.5},
            metadata={"tags": ["triage"]},
        )
        assert event.session_id == "abc-123"
        assert event.event_type == "chain_end"
        assert event.name == "triage_agent"
        assert event.latency_ms == 1200.0
        assert event.token_usage["total_tokens"] == 150
        assert event.ram_usage["diff_mb"] == 2.5
        assert event.metadata["tags"] == ["triage"]

    def test_to_dict_keys(self):
        """to_dict() should include all required keys."""
        event = LogEvent(
            event_type="llm_end",
            name="chatgroq",
            latency_ms=500.0,
        )
        d = event.to_dict()
        expected_keys = {
            "event_id", "session_id", "event_type", "name",
            "start_time", "end_time", "latency_ms",
            "token_usage", "ram_usage", "metadata",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_json_serialisable(self):
        """to_dict() result must be serialisable to JSON without errors."""
        event = LogEvent(
            session_id="s1",
            event_type="tool_end",
            name="rag_search",
            latency_ms=230.5,
            ram_usage={"start_mb": 200.0, "end_mb": 201.0, "diff_mb": 1.0},
        )
        json_str = json.dumps(event.to_dict())
        loaded = json.loads(json_str)
        assert loaded["name"] == "rag_search"
        assert loaded["latency_ms"] == 230.5

    def test_independent_mutable_defaults(self):
        """Mutable defaults (dicts) must be independent across instances."""
        a = LogEvent()
        b = LogEvent()
        a.token_usage["x"] = 1
        b.ram_usage["y"] = 2
        assert "x" not in b.token_usage
        assert "y" not in a.ram_usage
