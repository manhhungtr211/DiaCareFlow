# Tasks: UC-009 Chat History (Context)

**Input**: Design documents from `specs/UC-009-chat-history/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/api-contract.md](contracts/api-contract.md) · [quickstart.md](quickstart.md)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- All file paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency and config changes that all phases require.

- [x] T001 Add `CHAT_HISTORY_MAX_TOKENS` (default `4000`) to `.env` and load it in `src/config.py`
- [x] T002 Verify `langchain-core` version supports `trim_messages` — check `requirements.txt` or `pyproject.toml` and pin if needed

**Checkpoint**: Config and dependency baseline in place. All subsequent tasks can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend session store and graph compilation change — **must be complete before any user-story work**.

⚠️ **CRITICAL**: All user story tasks depend on this phase.

- [x] T003 Instantiate `MemorySaver` and recompile graph with `checkpointer=MemorySaver()` in `src/agents/graph.py` — update `compile_graph()` to accept and pass the checkpointer
- [x] T004 Add `session_id: str | None = None` field to `ChatRequest` in `src/api/schemas.py` (optional, default `None` for backward compat)
- [x] T005 [P] Add `chat_history: list` field to `AgentState` in `src/agents/state.py` (trimmed history for node consumption)
- [x] T006 Update `ask_langgraph(question, session_id)` in `src/agents/pipeline.py` to: auto-generate UUID if `session_id` is `None`, build `config = {"configurable": {"thread_id": session_id}}`, and pass it to `graph.invoke(initial_state, config=config)`
- [x] T007 Update `chat()` route handler in `src/api/routes.py` to extract `request.session_id` and forward it to `ask_langgraph(request.question, request.session_id)`

**Checkpoint**: Server restarts cleanly. Existing `POST /api/chat` without `session_id` still works (backward compat). `POST /api/chat` with a `session_id` persists thread state via MemorySaver.

---

## Phase 3: User Story 1 — Session History Storage (Priority: P1) 🎯 MVP

**Goal**: The system stores user and bot messages in the LangGraph `messages` field across requests within the same session, so the LLM has context for follow-up questions.

**Independent Test**:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tiểu đường là gì?", "session_id": "test-s1"}'

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Vậy bệnh đó có mấy loại?", "session_id": "test-s1"}'
```
Second response must discuss diabetes types — proving the LLM received prior context.

### Implementation for User Story 1

- [x] T008 [P] [US1] Add `HumanMessage` (using name is 'user') append to `AgentState.messages` for `user_input` at pipeline entry in `src/agents/pipeline.py` (before `graph.invoke`) — ensures user turn is stored in MemorySaver state
- [x] T009 [P] [US1] Add `trim_messages` call in a new helper `_build_chat_history(state)` in `src/agents/pipeline.py` (or a shared util `src/agents/history.py`) — trims `state["messages"]` to `CHAT_HISTORY_MAX_TOKENS` tokens using `ChatGroq` as token counter and `allow_partial=False`
- [x] T010 [US1] Populate `chat_history` field in initial state from trimmed messages in `src/agents/pipeline.py` `ask_langgraph()` — pass trimmed list as `chat_history` in the initial state dict passed to `graph.invoke`
- [x] T011 [US1] Inject `chat_history` into the LLM prompt in `src/agents/nodes/supervisor.py` — prepend formatted history turns before the current `user_input` in the supervisor prompt so intent classification uses context
- [x] T012 [US1] Inject `chat_history` into the RAG generation prompt in `src/rag/qa/generator.py` `generate()` — add history as a "Lịch sử hội thoại" section before the current question so the LLM resolves coreferences
- [x] T013 [US1] Update `response_agent_node` in `src/agents/nodes/response_agent.py` to read `chat_history` from state and pass it to `generate()` as a new parameter
- [x] T014 [US1] Append `AIMessage` (using name is 'assistant') with the final answer to messages at the end of `ask_langgraph()` in `src/agents/pipeline.py` — ensures bot turn is also stored in MemorySaver for subsequent requests
- [x] T014.1 Add message if small-talk into history
**Checkpoint**: Run quickstart Scenario 1 — second curl response correctly identifies "bệnh đó" as diabetes.

---

## Phase 4: User Story 2 — Contextual Coreference Resolution (Priority: P1)

**Goal**: The Harm Assessment node also receives chat history, preventing false positives on contextual follow-ups (e.g., "Nó có nguy hiểm không?" after a diabetes discussion should not be blocked).

**Independent Test**: Send `"Bệnh tiểu đường nguy hiểm không?"` followed by `"Nó có nguy hiểm không?"` with the same `session_id` — second question must not be refused/blocked.

### Implementation for User Story 2

- [x] T015 [US2] Don't inject `chat_history` into the LLM prompt in `src/agents/nodes/harm_assessment.py` — if `harm_assessment` determine messages are unsafe, dont add it into history
- [x] T016 [US2] Verify end-to-end: two-message session with pronoun-based follow-up routes correctly (not blocked) by testing with quickstart Scenario 1 coreference test

**Checkpoint**: Follow-up questions with pronouns pass harm assessment and produce accurate contextual answers.

---

## Phase 5: User Story 3 — Token-Limited History Window (Priority: P2)

**Goal**: Long sessions are automatically trimmed so the system never exceeds LLM context limits.

**Independent Test**: Send 25 messages in a single session. Verify no `context_length_exceeded` errors in server logs and responses remain coherent for the last 5 messages.

### Implementation for User Story 3

- [x] T017 [US3] Make `CHAT_HISTORY_MAX_TOKENS` configurable: read from `src/config.py` in `_build_chat_history()` (or `src/agents/history.py`) and use it as the `max_tokens` argument for `trim_messages`
- [x] T018 [US3] Add `strategy="last"` and `include_system=True` to the `trim_messages` call to always preserve the system message and most recent turns
- [x] T019 [US3] Add INFO-level logging in the trim helper reporting `original_count`, `trimmed_count`, and `token_estimate` after trimming

**Checkpoint**: Run quickstart Scenario 2 — 20+ messages send without errors; logs show trim activity.

---

## Phase 6: Frontend — Session ID Management

**Goal**: Frontend generates a `session_id` UUID on page mount and includes it in every chat request, enabling session isolation and automatic reset on page refresh (AC-3).

**Independent Test**: Open chat UI, send 2 messages ("Tiểu đường là gì?" → "Bệnh đó có mấy loại?"). Check Network tab — both requests carry the same `session_id`. Refresh page — next request carries a new `session_id`.

### Implementation

- [x] T020 [P] Generate `sessionId = crypto.randomUUID()` inside `useChat` hook (once, on mount via `useRef` or `useState` initializer) in `frontend/src/hooks/useChat.ts`
- [x] T021 [P] Update `sendMessage(question, sessionId)` signature in `frontend/src/services/chatService.ts` to include `session_id` in the POST body: `JSON.stringify({ question, session_id: sessionId })`
- [x] T022 Pass `sessionId` from `useChat` to `sendChatMessage` call in `frontend/src/hooks/useChat.ts`
-
**Checkpoint**: Run quickstart Scenario 3 — page refresh produces a new UUID and session context is lost as expected.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final polish, verification, and backward compatibility validation.
- [x] T023 print history on terminal
- [x] T024 Update module docstrings in modified files (`pipeline.py`, `graph.py`, `schemas.py`, `state.py`) to reflect UC-009 chat history changes
- [x] T025 Verify full quickstart.md — run all 4 scenarios end-to-end and confirm all expected outcomes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all user stories**
- **US1 — Phase 3**: Depends on Phase 2 completion
- **US2 — Phase 4**: Depends on Phase 3 (needs `chat_history` in state)
- **US3 — Phase 5**: Depends on Phase 3 (needs `_build_chat_history` helper)
- **Frontend — Phase 6**: **Independent** — can be done in parallel with Phase 3
- **Polish — Phase 7**: Depends on all phases complete

### User Story Dependencies

| Story | Phase | Depends On | Can Parallelize With |
|-------|-------|------------|----------------------|
| US1 (Session Storage) | 3 | Phase 2 | Phase 6 (frontend) |
| US2 (Coreference) | 4 | Phase 3 (T009, T010) | — |
| US3 (Token Trim) | 5 | Phase 3 (T009) | Phase 4 |
| Frontend | 6 | Phase 1 | Phases 3–5 |

### Within Each Phase

- Models/state changes → pipeline changes → node changes
- Backend foundational (Phase 2) → backend story tasks (Phases 3–5)
- Each story phase is a complete, independently testable increment

### Parallel Opportunities

- T004, T005 in Phase 2 can run in parallel (different files: `schemas.py` vs `state.py`)
- T008, T009 in Phase 3 can run in parallel (pipeline entry vs helper function)
- T020, T021 in Phase 6 can run in parallel (different files: hook vs service)
- Phase 6 (frontend) entirely parallel with Phase 3–5 (backend stories)

---

## Parallel Example: Phase 2 (Foundational)

```text
Can run simultaneously:
  Task T004: Add session_id to ChatRequest in src/api/schemas.py
  Task T005: Add chat_history field to AgentState in src/agents/state.py

Must run after:
  Task T003 (graph compilation) → T006 (pipeline) → T007 (route handler)
```

## Parallel Example: Phase 6 (Frontend)

```text
Can run simultaneously with any Phase 3–5 backend task:
  Task T020: Generate sessionId in frontend/src/hooks/useChat.ts
  Task T021: Add session_id to POST body in frontend/src/services/chatService.ts
```

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1–3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (graph + API schema)
3. Complete Phase 3: US1 (pipeline + node history injection)
4. **STOP and VALIDATE**: Run quickstart Scenario 1 — pronoun coreference works
5. Deploy / demo if ready

### Incremental Delivery

1. Phases 1–2 → Foundation ready (MemorySaver, session_id API)
2. Phase 3 → US1 working (session history storage + LLM context)
3. Phase 4 → US2 working (harm assessment context-aware)
4. Phase 5 → US3 working (token trimming enforced)
5. Phase 6 → Frontend wired (session UUID, isolation on refresh)
6. Phase 7 → Polish + final validation

---

## Notes

- `[P]` tasks modify different files with no shared state — safe to parallelize
- `[Story]` label maps each task to its user story for traceability
- No tests are specified in the feature spec — test tasks are omitted per skill rules
- `MemorySaver` is in-memory only; server restart clears all sessions (by design, AC-3)
- `trim_messages` requires a token counter compatible with the model; use `ChatGroq` instance or `token_counter=len` as fallback
- The `messages` field in `AgentState` already has the `add_messages` reducer from `MessagesState` — do not redefine it
