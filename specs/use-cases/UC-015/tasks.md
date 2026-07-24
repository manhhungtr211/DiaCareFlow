# Tasks: UC-015 Cải tiến quy trình xử lý câu hỏi người dùng qua hệ thống Multi-Agent (Refactor Kiến trúc)

**Input**: Design documents from `/specs/use-cases/UC-015/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., AC-1, AC-2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Verify and synchronize existing multi-agent architecture setup.
- [X] T002 Review `specs/use-cases/UC-015/data-model.md` for specific model reversions (e.g., `FactorState`, `HarmState`, `SuggestionState`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Update `src/agents/state.py` to explicitly define `FactorState`, `HarmState`, `SuggestionState`, `FactorOutputState`, `HarmOutputState`, and `SuggestionOutputState` as per `data-model.md`.
- [X] T004 Update `AgentState` in `src/agents/state.py` to match the exact field types from `data-model.md` (e.g., changing `chat_history` back to `List[Any]`, and ensuring Reducer outputs use the correct types).
- [X] T005 Update node files (`src/agents/nodes/factor_agent.py`) to if fan-in then `factor_task`, `harm_task`, `suggestion_task` was updated
- [X] T006 Update node files (`src/agents/nodes/factor_agent.py`, `src/agents/nodes/harm_agent.py`, `src/agents/nodes/suggestion_agent.py`) to use the specific `*State` and `*OutputState` types in their signatures and docstrings and using to `factor_task`, `harm_task`, `suggestion_task` to create sub question by LLM before using tool

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: AC-1 - Trả lời câu hỏi hợp lệ thành công (Happy Path) 🎯 MVP

**Goal**: Hệ thống có khả năng xử lý câu hỏi an toàn (VD: "Người tiền tiểu đường nên ăn gì?") bằng cách chia task song song cho 3 Agent và tổng hợp bằng Response Agent.

**Independent Test**: Gửi request an toàn qua `curl` và kiểm tra response không bị hallucination.

### Tests for AC-1 ⚠️

- [X] T006 [P] [AC-1] Fix/update unit test `tests/unit/agents/test_state.py` to validate the new Pydantic/TypedDict state models.
- [X] T007 [P] [AC-1] Update unit tests `test_factor_agent.py`, `test_suggestion_agent.py`, and `test_harm_agent.py` to mock and expect the specific `*State` dictionaries.

### Implementation for AC-1

- [X] T008 [P] [AC-1] Update `src/agents/nodes/supervisor_node.py` to ensure it populates the tasks correctly matching the new state expectations.
- [X] T009 [P] [AC-1] Ensure `response_agent.py` gracefully handles the new `StateOutput` dict formats as aggregated by LangGraph.
- [ ] T010 [AC-1] Run unit tests to confirm all agents process their inputs and generate valid outputs.

**Checkpoint**: At this point, AC-1 should be fully functional and testable independently

---

## Phase 4: AC-2 - Triage chặn câu hỏi độc hại

**Goal**: Triage Agent nhận diện câu hỏi nguy hiểm/không an toàn và lập tức bypass toàn bộ flow, trả về thông báo lỗi.

**Independent Test**: Gửi câu hỏi khẩn cấp qua `curl` và xác minh sub-agents không được kích hoạt.

### Tests for AC-2 ⚠️

- [X] T011 [P] [AC-2] Ensure `tests/integration/test_pipeline_multi_agent.py` passes the unsafe path assertion with the current `triage_node.py` logic.

### Implementation for AC-2

- [X] T012 [P] [AC-2] Verify `src/agents/nodes/triage_node.py` cleanly outputs `is_safe=False` matching `data-model.md` and routes directly to response.

**Checkpoint**: At this point, AC-2 should be fully functional and testable independently

---

## Phase 5: Polish & Final Review

**Purpose**: Cross-cutting concerns, cleanup, and final validation

- [ ] T013 Run full `pytest` regression suite to ensure 100% pass rate.
- [ ] T014 Execute manual testing with CLI curl commands as documented in `quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies
1. **Phase 1** must complete first.
2. **Phase 2** must complete before Phase 3 and Phase 4.
3. **Phase 3 and Phase 4** can be executed in parallel.
4. **Phase 5** runs last.

### Parallel Opportunities
```text
Phase 3 Implementation:
  T008 ‖ T009 
  → T010

Phase 3/4 Tests:
  T006 ‖ T007 ‖ T011
```

## Implementation Strategy

1. **State First**: We will implement the TypedDict state structures defined in `data-model.md` to ensure type safety.
2. **Node Updates**: We will propagate these type changes to the node signatures and docstrings.
3. **Test Alignment**: We will ensure unit tests align with the strictly typed state outputs.
4. **Integration**: We will run the full suite to verify end-to-end functionality.
