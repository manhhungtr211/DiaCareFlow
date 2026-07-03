# Data Model: UC-010 Bypass RAG

**Feature**: UC-010 — Trò chuyện thông thường (Bypass RAG)
**Date**: 2026-07-03

---

## AgentState — new field

**File**: `src/agents/state.py`

```python
class AgentState(MessagesState):
    # --- Input ---
    user_input: str

    # --- Harm Assessment output ---
    is_safe: bool
    harm_task: SafetyCategory

    # --- RAG output ---
    rag_context: list

    # --- Response output ---
    suggestion_context: dict

    # --- Metadata ---
    messageId: str
    nodes_visited: Annotated[list[str], operator.add]
    error: Optional[str]
```

`SafetyCategory` enum is **unchanged** — harm classification and intent classification are separate concerns:

| Enum | Owned by | Values |
|------|----------|--------|
| `SafetyCategory` | `harm_assessment_node` | `SAFE`, `PRESCRIPTION`, `DIAGNOSIS`, `EMERGENCY` |
| `intent: str` | `supervisor_node` |

---

## Routing State Machine

```
user_input
    │
    ▼
harm_assessment_node        (unchanged)
    │  sets: is_safe, harm_task
    │
    ├── is_safe = False  ──────────────────────────────► supervisor → END
    │                                                    (refusal already set)
    │
    └── is_safe = True
            │
            ▼
        supervisor_node          (UPGRADED: now classifies intent)
            │  
            │
            ├── intent != "DIABETES" ─────────────────► response_agent
            │                                            (generate_small_talk)
            │
            └── intent = "DIABETES" ──────────────────► rag_agent → response_agent
                                                         (generate with chunks)

