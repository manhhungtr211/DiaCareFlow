# Design: UC-012 Multi-Agent Architecture

**Date**: 2026-07-17 | **Status**: Implemented | **Spec**: [UC-012-refactor-architecture.md](specs/UC-012-refactor-architecture.md)

---

## Luồng xử lý (Flow Diagram)

```
User Query
    │
    ▼
┌─────────────────┐
│  triage_agent   │  (harm_assessment_node, renamed in graph)
│  Safety check   │
└────────┬────────┘
         │
    ┌────┴──────┐
    │           │
is_safe=False   is_safe=True
    │           │
    │           ▼
    │   ┌───────────────┐
    │   │  supervisor   │  Classify: SMALL_TALK vs DIABETES
    │   └───────┬───────┘
    │           │
    │      ┌────┴──────────────┐
    │      │                   │
    │  SMALL_TALK          DIABETES
    │      │                   │
    │      │         ┌─────────┴─────────┐
    │      │         │ Send API fan-out   │
    │      │         │ (parallel)        │
    │      │    ┌────┴────┐  ┌────┴────┐  ┌─────┴─────┐
    │      │    │ factor  │  │suggest. │  │harm_sub   │
    │      │    │ agent   │  │ agent   │  │ agent     │
    │      │    └────┬────┘  └────┬────┘  └─────┬─────┘
    │      │         │            │              │
    │      │         └────────────┴──────────────┘
    │      │                      │
    │      │              ┌───────┴───────┐
    │      │              │  aggregate    │  (fan-in, pure pass-through)
    │      │              └───────┬───────┘
    │      │                      │
    └──────┴──────────────────────┤
                                  ▼
                       ┌──────────────────┐
                       │  response_agent  │  Synthesize final answer
                       └──────────┬───────┘
                                  │
                                  ▼
                              User Answer
```

---

## Node Responsibilities

| Node | Role | LLM Call | Tool |
|------|------|----------|------|
| `triage_agent` | Safety check (dùng lại `harm_assessment_node`) | ✅ | `check_guardrail()` |
| `supervisor` | Intent classification (SMALL_TALK vs DIABETES) | ✅ | — |
| `factor_agent` | Root cause / mechanism analysis | ✅ | RAG, web_search  |
| `suggestion_agent` | Practical solution suggestions | ✅ | web_search , RAG |
| `harm_sub_agent` | Risk / safety warnings assessment | ✅ | RAG, web_search |
| `aggregate` | Fan-in sync point | ❌ | — |
| `response_agent` | Final answer synthesis from sub-agent summaries | ✅ | — |

---

## State Fan-in Mechanism

Sub-agents write to `Annotated[list, operator.add]` fields. LangGraph merges results from parallel nodes automatically:

```python
# After all 3 sub-agents complete:
state["factor_results"]     = [{"factor_summary": "...", "sources": [...]}]
state["suggestion_results"] = [{"suggestion_summary": "..."}]
state["harm_sub_results"]   = [{"harm_summary": "..."}]
state["nodes_visited"]      = ["factor_agent", "suggestion_agent", "harm_sub_agent"]
state["errors"]             = []  # or errors from failed sub-agents
```

---

## Error Handling

- Each sub-agent wraps its body in `try/except`.
- On failure: appends to `state["errors"]` (Annotated list), returns `{field: []}`.
- `response_agent` checks for empty results and handles gracefully.
- Flow never crashes — Response Agent always runs and produces a user-facing message.

---

## Backward Compatibility

| Constraint | Status |
|-----------|--------|
| `ask_langgraph()` signature unchanged | ✅ |
| `Answer` dataclass unchanged | ✅ |
| `_state_to_answer()` reads from `suggestion_context` | ✅ |
| `pipeline.py` entry point unchanged | ✅ |

---

## Implementation Files

| File | Change |
|------|--------|
| `src/agents/state.py` | Added `factor_results`, `suggestion_results`, `harm_sub_results`, `errors`; removed `rag_context`, `error` |
| `src/agents/graph.py` | Full topology rewrite: triage_agent, Send fan-out, aggregate node |
| `src/agents/pipeline.py` | Updated initial_state dict; `_state_to_answer` uses `errors` list |
| `src/agents/nodes/supervisor.py` | Refactored: SMALL_TALK vs DIABETES, writes to `errors` list |
| `src/agents/nodes/response_agent.py` | Reads from 3 sub-agent result fields instead of `rag_context` |
| `src/agents/nodes/factor_agent.py` | **NEW** — RAG, web_search  |
| `src/agents/nodes/suggestion_agent.py` | **NEW** — web_search, RAG  |
| `src/agents/nodes/harm_agent.py` | **NEW** — RAG, web_search  |
| `src/agents/nodes/__init__.py` | Exports 3 new nodes |
