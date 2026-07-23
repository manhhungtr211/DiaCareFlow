# Data Model: Add Tracking

## LogEvent

Represents an execution event in the LangGraph pipeline (e.g., node start/end, LLM start/end, tool start/end).

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` | Unique identifier for the event (UUID). |
| `session_id` | `str` | The conversation session identifier this event belongs to. |
| `event_type` | `str` | Type of event (e.g., `chain_start`, `chain_end`, `llm_end`). |
| `name` | `str` | Name of the node, tool, or LLM being executed. |
| `start_time` | `float` | Unix timestamp of when the event started. |
| `end_time` | `float` | Unix timestamp of when the event ended (if applicable). |
| `latency_ms` | `float` | Latency of the event in milliseconds. |
| `token_usage` | `dict` | Token usage for LLM calls (e.g., `prompt_tokens`, `completion_tokens`, `total_tokens`). |
|`ram_usage` | `dict` | RAM usage for LLM calls (e.g., `prompt_tokens`, `completion_tokens`, `total_tokens`). |
| `metadata` | `dict` | Any additional context (e.g., input args, tags, etc.). |
