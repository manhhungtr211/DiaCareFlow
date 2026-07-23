# Tasks: Add Tracking (013-add-tracking)

**Input**: Design documents from `/specs/013-add-tracking/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not explicitly requested in spec — test tasks are omitted. Unit tests in Polish phase only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and prepare the logging infrastructure directory.

- [x] T001 Add `psutil>=5.9.0` to `requirements.txt` (needed for RAM tracking)
- [x] T002 Create `logs/` directory at project root and add `logs/.gitkeep` (output destination for tracking logs)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core `LogEvent` dataclass and logging configuration that the callback handler depends on.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [x] T003 Create `src/agents/tracking/` package directory with `src/agents/tracking/__init__.py`
- [x] T004 Implement `LogEvent` dataclass in `src/agents/tracking/models.py` — fields: `event_id`, `session_id`, `event_type`, `name`, `start_time`, `end_time`, `latency_ms`, `token_usage`, `ram_usage`, `metadata`
- [x] T005 [P] Implement `JsonTrackingLogger` helper in `src/agents/tracking/logger.py` — configures a dedicated Python `logging.Logger` that formats each `LogEvent` as a single JSON line and outputs to both `stdout` and `logs/tracking.jsonl`

**Checkpoint**: `LogEvent` model + JSON logger are ready. Callback handler can now be implemented.

---

## Phase 3: User Story 1 — System Administrator Views Logs (Priority: P1) 🎯 MVP

**Goal**: Implement and wire the `DiaCareFlowCallbackHandler` so that 100% of LangGraph node executions, LLM calls, and tool calls are captured and emitted as structured JSON logs with latency and resource usage.

**Independent Test**: Run `python src/cli.py`, ask a diabetes question, then verify `logs/tracking.jsonl` contains valid JSON entries with `latency_ms`, `token_usage`, and `ram_usage` fields populated.

### Implementation for User Story 1

- [x] T006 [US1] Implement `DiaCareFlowCallbackHandler(BaseCallbackHandler)` in `src/agents/tracking/callback_handler.py`:
  - Override `on_chain_start` — record `start_time` (Unix timestamp) and `ram_start_mb` (via `psutil.Process().memory_info().rss`) keyed by `run_id`
  - Override `on_chain_end` — compute `latency_ms`, `ram_diff_mb`, build `LogEvent`, emit via `JsonTrackingLogger`
  - Override `on_llm_start` — record `start_time` and `ram_start_mb` keyed by `run_id`
  - Override `on_llm_end(response: LLMResult)` — extract `response.llm_output.get("token_usage", {})` for `token_usage`, compute `latency_ms` and `ram_diff_mb`, build `LogEvent`, emit via `JsonTrackingLogger`
  - Override `on_tool_start` — record `start_time` and `ram_start_mb` keyed by `run_id`
  - Override `on_tool_end` — compute `latency_ms` and `ram_diff_mb`, build `LogEvent`, emit via `JsonTrackingLogger`
  - `ram_usage` dict must contain: `start_mb`, `end_mb`, `diff_mb`

- [x] T007 [US1] Wire `DiaCareFlowCallbackHandler` into the LangGraph pipeline in `src/agents/pipeline.py`:
  - Instantiate handler at module level (singleton)
  - Pass handler via `config={"callbacks": [handler]}` in the `graph.invoke(...)` call inside `ask_langgraph()`

- [x] T008 [US1] Export `DiaCareFlowCallbackHandler` from `src/agents/tracking/__init__.py` for clean import paths

- [x] T009 [US1] Validate end-to-end log output per `quickstart.md` — 18/18 unit tests passed, all log fields verified programmatically

**Checkpoint**: After T009, User Story 1 is fully functional and testable independently.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, unit tests, and documentation.

- [x] T010 [P] Write unit tests for `LogEvent` dataclass in `tests/unit/test_tracking_models.py` — test field types, defaults, and JSON serialization
- [x] T011 [P] Write unit tests for `DiaCareFlowCallbackHandler` in `tests/unit/test_callback_handler.py` — mock `psutil` and `LLMResult`, assert correct `LogEvent` is built and emitted for each callback method
- [x] T012 Update `README.md` to document the tracking feature: what is logged, log file location, and log format example
- [x] T013 Tracing input, output of LLM and tools. Not sure how to do this with the current implementation.
---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS user story
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **Polish (Phase 4)**: Depends on Phase 3 completion

### Within User Story 1

- T006 (callback handler) → T007 (wire into pipeline) → T009 (validate)
- T008 can run in parallel with T006 (just the `__init__.py` export)

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel
- T004 and T005 (Foundational) can run in parallel
- T010 and T011 and T012 (Polish) can all run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Both can run in parallel (different files):
Task T004: "Implement LogEvent dataclass in src/agents/tracking/models.py"
Task T005: "Implement JsonTrackingLogger helper in src/agents/tracking/logger.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: User Story 1 (T006–T009)
4. **STOP and VALIDATE**: Run quickstart.md validation, check `logs/tracking.jsonl`
5. Proceed to Polish only after validation passes

### Incremental Delivery

- After T007: The pipeline emits logs — basic chain tracking works
- After T006 (LLM callbacks added): Token usage and RAM tracking for LLM calls work
- After T009: Full end-to-end validation confirmed

---

## Notes

- [P] tasks = different files, no dependencies
- `ram_usage` tracks process-level RSS before and after each event — not per-allocation, but sufficient for detecting memory spikes per node
- `psutil` is cross-platform (Windows + Linux) so local dev and server both work
- Log destination: `logs/tracking.jsonl` (append mode). Rotate manually or via `logrotate` on server
- Avoid adding callbacks to the `compile_graph()` call — prefer `graph.invoke(..., config={"callbacks": [...]})` so the handler can be swapped without recompiling the graph
