"""
Data model for LangGraph pipeline tracking events.

LogEvent represents a single instrumentation event captured by the
DiaCareFlowCallbackHandler — covering node (chain), LLM, and tool executions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogEvent:
    """
    A single tracked event in the LangGraph pipeline.

    Fields
    ------
    event_id     : Unique UUID for this event instance.
    session_id   : The conversation thread_id this event belongs to.
    event_type   : Callback type — e.g. "chain_start", "chain_end",
                   "llm_start", "llm_end", "tool_start", "tool_end".
    name         : Name of the node, LLM, or tool being executed.
    start_time   : Unix timestamp (seconds) when the event began.
    end_time     : Unix timestamp (seconds) when the event finished.
                   None if not yet complete.
    latency_ms   : Duration in milliseconds (end_time - start_time) * 1000.
                   0.0 if end_time is not available.
    token_usage  : Token counts from the LLM response, e.g.
                   {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165}.
                   Empty dict for non-LLM events.
    ram_usage    : Process RSS memory captured around the event, e.g.
                   {"start_mb": 310.2, "end_mb": 312.5, "diff_mb": 2.3}.
                   Empty dict if psutil is unavailable.
    metadata     : Arbitrary extra context (tags, run_id, inputs, etc.).
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    event_type: str = ""
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    latency_ms: float = 0.0
    token_usage: dict[str, Any] = field(default_factory=dict)
    ram_usage: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for JSON serialisation."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "ram_usage": self.ram_usage,
            "metadata": self.metadata,
        }
