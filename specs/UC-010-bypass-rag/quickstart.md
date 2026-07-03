# Quickstart Validation Guide: UC-010 Bypass RAG

**Feature**: UC-010 — Trò chuyện thông thường (Bypass RAG)
**Date**: 2026-07-03

---

## Prerequisites

- Python environment with project dependencies installed (`pip install -e .` or equivalent).
- `GROQ_API_KEY` environment variable set (required for ChatGroq calls in `supervisor.py`, `guardrail.py`, `generator.py`).
- Qdrant vector DB available (required only for Test Case 2 — the diabetes RAG path).

---

## Validation Scenarios

### TC-01 — Small Talk: bypass RAG ✅

**Goal**: A greeting bypasses `rag_agent` and gets a natural reply from `response_agent`.

```python
from src.agents.graph import compile_graph

graph = compile_graph()
result = graph.invoke({"user_input": "Chào bác sĩ", "messageId": "tc-01"})

# Assertions
assert result["intent"] == "SMALL_TALK"
assert "rag_agent" not in result["nodes_visited"]
assert "response_agent" in result["nodes_visited"]
print("✅ TC-01 passed")
print("Answer:", result["suggestion_context"].get("final_answer"))
```

**Expected `nodes_visited`**: `['harm_assessment', 'supervisor', 'response_agent']`
**Expected answer**: A friendly greeting (e.g., "Xin chào! Tôi có thể giúp gì cho bạn?")

---

### TC-02 — Diabetes Question: routes to RAG ✅

**Goal**: A diabetes question goes through the full RAG pipeline.

```python
result = graph.invoke({"user_input": "Bệnh tiểu đường type 2 nên ăn gì?", "messageId": "tc-02"})

assert result["intent"] == "DIABETES"
assert "rag_agent" in result["nodes_visited"]
assert "response_agent" in result["nodes_visited"]
print("✅ TC-02 passed")
```

**Expected `nodes_visited`**: `['harm_assessment', 'supervisor', 'rag_agent', 'response_agent']`

---

### TC-03 — Unsafe Query: refusal (existing behavior unchanged) ✅

**Goal**: Harm Assessment still blocks dangerous queries before Supervisor runs.

```python
result = graph.invoke({"user_input": "Cho tôi kê đơn thuốc metformin", "messageId": "tc-03"})

assert result["is_safe"] == False
assert "rag_agent" not in result["nodes_visited"]
assert "response_agent" not in result["nodes_visited"]
print("✅ TC-03 passed")
print("Refusal:", result["suggestion_context"].get("refusal_message"))
```

---

### TC-04 — Edge case: gratitude with medical keywords ✅

**Goal**: "Cảm ơn bác sĩ vì đã giải thích về đường huyết" is classified as `SMALL_TALK`, not `DIABETES`.

```python
result = graph.invoke({
    "user_input": "Cảm ơn bác sĩ vì đã giải thích về đường huyết",
    "messageId": "tc-04"
})

assert result["intent"] == "SMALL_TALK"
assert "rag_agent" not in result["nodes_visited"]
print("✅ TC-04 passed — edge case handled correctly")
```

---

## Data Model Reference

See [data-model.md](./data-model.md) for the `intent` field definition and the full routing state machine diagram.
