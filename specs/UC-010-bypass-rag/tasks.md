# Tasks: UC-010 Bypass RAG

**Input**: Design documents from `specs/UC-010-bypass-rag/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [quickstart.md](./quickstart.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P]-marked tasks
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Verify the existing pipeline compiles and baseline state is captured before any changes.

- [x] T001 Read and understand `src/agents/graph.py`, `src/agents/state.py`, `src/agents/nodes/supervisor.py`, `src/agents/nodes/response_agent.py` to establish baseline
- [x] T002 Confirm the existing graph builds and a sample invocation succeeds (e.g., `python -c "from src.agents.graph import compile_graph; compile_graph()"`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: State changes that both user stories depend on — must be complete before US1 or US2.

**⚠️ CRITICAL**: Both user story phases depend on T003 and T004 below.

- [x] T003 Add `intent: str` field to `AgentState` in `src/agents/state.py` (after `harm_task`, value will be `"DIABETES"` or the supervisor's inline small-talk reply text)
- [x] T004 Add `small_talk_reply: str` field to `AgentState` in `src/agents/state.py` to carry the supervisor's pre-generated conversational answer when intent is not DIABETES (avoids overloading `intent` with reply text)

**Checkpoint**: `AgentState` now has `intent: str` and `small_talk_reply: str`. Graph still compiles unchanged.

---

## Phase 3: User Story 1 — Intent Classification & Small Talk Reply (Priority: P1) 🎯 MVP

**Goal**: Supervisor classifies each safe message with a single LLM call. If it's small talk, the LLM reply is captured and routed directly to the response agent — no vector search triggered.

**Independent Test** (from quickstart.md TC-01 & TC-04):
```python
result = graph.invoke({"user_input": "Chào bác sĩ", "messageId": "tc-01"})
assert "rag_agent" not in result["nodes_visited"]
assert result["suggestion_context"]["final_answer"]  # non-empty friendly reply
```

### Implementation for User Story 1

- [x] T005 [US1] Rewrite `supervisor_node` in `src/agents/nodes/supervisor.py`:
  - Call `ChatGroq` with a combined classify-and-respond prompt:
    - If small talk: LLM returns the conversational reply text (no label needed)
    - If diabetes/health: LLM returns the single word `DIABETES`
  - Parse response: if `"DIABETES"` in content → set `intent = "DIABETES"`, `small_talk_reply = ""`; else → set `intent = "SMALL_TALK"`, `small_talk_reply = response.content.strip()`
  - Default on LLM error: `intent = "DIABETES"`, `small_talk_reply = ""` (fail-safe)
  - Return `{"intent": intent, "small_talk_reply": small_talk_reply, "nodes_visited": ["supervisor"]}`

- [x] T006 [US1] Update `_route_after_supervisor` in `src/agents/graph.py`:
  - Routing logic:
    ```python
    if not state.get("is_safe", True): return END
    if state.get("intent") == "SMALL_TALK":  return "response_agent"
    return "rag_agent"
    ```
  - Update `add_conditional_edges` map to include `"response_agent": "response_agent"` as a new destination

- [x] T007 [US1] Update `response_agent_node` in `src/agents/nodes/response_agent.py`:
  - Add branch at the top: if `state.get("intent") != "DIABETES"`:
    - Read `small_talk_reply = state.get("small_talk_reply", "")`
    - Return `{"suggestion_context": {"final_answer": small_talk_reply, "sources": [], "is_refused": False, "refuse_reason": None}, "nodes_visited": ["response_agent"]}`
  - Existing `generate(query, context)` path unchanged for `intent == "DIABETES"`

**Checkpoint (US1 complete)**: Send "Chào bác sĩ" → `nodes_visited` must NOT contain `rag_agent`; `suggestion_context.final_answer` must be a non-empty friendly sentence.

---

## Phase 4: User Story 2 — Diabetes Questions Still Route to RAG (Priority: P1)

**Goal**: Verify that the updated supervisor does not break the existing RAG path for diabetes questions.

**Independent Test** (from quickstart.md TC-02):
```python
result = graph.invoke({"user_input": "Bệnh tiểu đường type 2 nên ăn gì?", "messageId": "tc-02"})
assert "rag_agent" in result["nodes_visited"]
assert result["suggestion_context"].get("final_answer")
```

### Implementation for User Story 2

- [x] T008 [US2] Verify the supervisor prompt in `src/agents/nodes/supervisor.py` correctly returns `DIABETES` for health questions — adjust prompt wording if test fails (no code-path change needed, only prompt tuning)
- [x] T009 [US2] Confirm `response_agent_node` in `src/agents/nodes/response_agent.py` still calls `generate(query, context)` when `intent == "DIABETES"` — add a defensive check that `rag_context` is not empty before calling `generate()`, else return a "no information found" answer

**Checkpoint (US2 complete)**: Send "Bệnh tiểu đường nên ăn gì?" → `nodes_visited` contains `rag_agent`; answer is document-grounded.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Robustness, logging, and validation across both stories.

- [x] T010 [P] Add logging to `supervisor_node` in `src/agents/nodes/supervisor.py` — log `intent` classification result and whether small-talk reply was generated
- [x] T011 [P] Update docstrings in `src/agents/nodes/supervisor.py` and `src/agents/nodes/response_agent.py` to reflect new behavior (intent field, small_talk_reply path)
- [x] T012 Update `src/agents/graph.py` docstring/comment in `build_graph()` to reflect new topology: `supervisor → [SMALL_TALK → response_agent | DIABETES → rag_agent → response_agent]`
- [x] T013 Run all 4 quickstart validation scenarios from `specs/UC-010-bypass-rag/quickstart.md` (TC-01, TC-02, TC-03, TC-04) and confirm all pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks Phase 3 and Phase 4**
- **Phase 3 (US1)**: Depends on Phase 2 — T005 → T006 → T007 (sequential within story)
- **Phase 4 (US2)**: Depends on Phase 2; can start in parallel with Phase 3 if T008/T009 are isolated
- **Phase 5 (Polish)**: Depends on Phase 3 + Phase 4 complete

### Within Each User Story

- **US1**: T005 (supervisor) must complete before T006 (graph router) and T007 (response_agent) — T006 and T007 can then run in parallel [P]
- **US2**: T008 and T009 are independent [P]

### Parallel Opportunities

```bash
# After Phase 2 completes:
# US1 — T005 first, then T006 and T007 in parallel
Task T006: Update graph.py routing
Task T007: Update response_agent.py branching

# US2 — T008 and T009 in parallel
Task T008: Tune supervisor prompt for DIABETES
Task T009: Add defensive rag_context check in response_agent

# Polish — T010 and T011 in parallel
Task T010: Add logging to supervisor
Task T011: Update docstrings
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup baseline
2. Complete Phase 2: Add `intent` + `small_talk_reply` to `AgentState`
3. Complete Phase 3: Implement US1 (T005 → T006 → T007)
4. **STOP and VALIDATE**: Send "Chào bác sĩ" — confirm no `rag_agent` in `nodes_visited`
5. Run TC-01 and TC-04 from quickstart.md

### Incremental Delivery

1. Setup + Foundational → `AgentState` ready
2. US1 complete → bypass RAG for small talk ✅
3. US2 verified → RAG path confirmed unchanged ✅
4. Polish → logs, docstrings, quickstart validation ✅

---

## Notes

- `intent` field carries `"SMALL_TALK"` or `"DIABETES"` — do NOT store the reply text in `intent`
- `small_talk_reply` carries the LLM's conversational answer (set by supervisor, read by response_agent)
- `harm_assessment_node`, `guardrail.py`, `rag_agent.py`, `data_models.py` are **not modified**
- Default on supervisor LLM error: `intent = "DIABETES"` (fail-safe — prefer RAG over missing a medical question)
- Commit after T007 so the small-talk bypass is independently deployable before tackling US2
