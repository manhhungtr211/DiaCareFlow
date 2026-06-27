# Tasks: UC-005 — Multi-Agent Pipeline LangGraph

**Input**: Design documents from `/specs/UC-005-multi-agent-langgraph/`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `src/agents/` module structure and install LangGraph dependency

- [x] T001 Create `src/agents/` package directory with `src/agents/__init__.py` and `src/agents/nodes/__init__.py`
- [x] T002 Add `langgraph>=1.2.6` to `requirements.txt` and install dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define the shared `AgentState` and configuration that ALL agent nodes depend on. MUST complete before any user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `SafetyCategory` enum(fields: question, is_safe, safety_category) and `AgentState` in `src/agents/state.py` per data-model.md schema (user_input, messages, harm_task, suggestion_context, messageId)

**Checkpoint**: Foundation ready — `AgentState` and config defined, user story implementation can begin

---

## Phase 3: User Story 1 — Hỏi đáp an toàn qua Multi-Agent Pipeline (Priority: P1) 🎯 MVP

**Goal**: Safe diabetes questions flow through  Harm Assessment (SAFE)  → Supervisor  → RAG Agent → Response Agent, returning an accurate answer with source references.

**Independent Test**: Call `ask_langgraph("Tiền tiểu đường là gì?")` from Python and verify the returned Answer contains content from RAG documents plus source citations

### Implementation for User Story 1
- [ ] T005 [US1] Implement Harm Assessment Agent node in `src/agents/nodes/harm_assessment.py` — wrap `src/rag/qa/guardrail.py`, evaluate question safety, set `is_safe`, `safety_category` (SAFE/PRESCRIPTION/DIAGNOSIS/EMERGENCY), and `refusal_message` in AgentState. Include try/catch per FR-007 with error written to state ->? nếu input text là trống hoặc chứa ký tự đặc biệt thì trả kết quả là vui lòng nhập lại câu hỏi, không chuyển tiếp node khác
- [x] T006 [US1] append "harm_assessment" to nodes_visited, validate non-empty question per edge case: return error state for empty/special-char-only input, routes to Supervisor Agent node in `src/agents/nodes/supervisor.py` — receives question, initializes `nodes_visited`, 

- [x] T007 [US1] Implement RAG Agent node in `src/agents/nodes/rag_agent.py` — wrap `src/rag/qa/retriever.py`, retrieve document chunks for the question, write `rag_context` and `rag_query_vector` to `AgentState`. Include try/catch per FR-007 (Qdrant unavailable → error state with clear connection message).
- [x] T008 [US1] Implement Response Agent node in `src/agents/nodes/response_agent.py` — wrap `src/rag/qa/generator.py`, read `rag_context` from state, generate final answer, write `final_answer` and `sources` to `AgentState`. Include try/catch per FR-007.
- [x] T009 [US1] Build StateGraph and compile in `src/agents/graph.py` — add nodes (supervisor, harm_assessment, rag_agent, response_agent), add edges (START → harm_assessment → supervisor), add conditional edge after harm_assessment (is_safe=True → rag_agent → response_agent → END, is_safe=False → END)
- [x] T010 [US1] Implement entry point `ask_langgraph(question, top_k)` in `src/agents/pipeline.py` — instantiate compiled graph, invoke with initial `AgentState`, measure `processing_time_ms`, convert final state to `Answer` dataclass (map final_answer→text, sources→sources, refusal_message→refuse_reason, is_safe→is_refused), handle error state with fallback Answer.

**Checkpoint**: At this point, the full happy-path pipeline works — safe questions produce RAG-based answers through the LangGraph multi-agent graph.

---

## Phase 4: User Story 2 — Từ chối truy vấn nguy hiểm qua Harm Assessment Agent (Priority: P1)

**Goal**: Dangerous questions (prescriptions, diagnoses, emergencies) are identified by Harm Assessment Agent, the pipeline is short-circuited, and a standardized medical refusal message is returned. RAG Agent and Response Agent are NOT invoked.

**Independent Test**: Send `ask_langgraph("Tôi bị tiểu đường type 2, cho tôi đơn thuốc Metformin")` and verify 100% blocked with appropriate refusal message. Verify nodes_visited does NOT include rag_agent or response_agent.

### Implementation for User Story 2

- [x] T011 [US2] Add refusal message mapping in `src/agents/nodes/harm_assessment.py` — map `SafetyCategory` to standard medical refusal messages: PRESCRIPTION → "Xin lỗi, tôi không thể kê đơn thuốc. Vui lòng tham khảo ý kiến bác sĩ.", DIAGNOSIS → "Xin lỗi, tôi không thể chẩn đoán bệnh. Vui lòng đến cơ sở y tế.", EMERGENCY → "⚠️ Tình huống khẩn cấp! Vui lòng gọi 115 hoặc đến phòng cấp cứu ngay."
- [x] T012 [US2] Validate conditional routing in `src/agents/graph.py` — ensure when `is_safe=False`, the graph routes directly to END, bypassing rag_agent and response_agent nodes entirely.
- [x] T013 [US2] Handle refusal path in `src/agents/pipeline.py` — when `is_safe=False` in final state, construct Answer with `is_refused=True`, `refuse_reason=safety_category`, `text=refusal_message`, and empty sources list.

**Checkpoint**: Harm Assessment path fully works — dangerous queries are blocked with category-specific medical refusals.

---

## Phase 5: User Story 3 — Pipeline tương thích ngược với CLI hiện tại (Priority: P2)

**Goal**: `python -m src.cli ask` works exactly as before after refactor. No changes to CLI arguments, output format, or exit codes.

**Independent Test**: Run `python -m src.cli ask` and enter both safe and dangerous questions — verify identical UX to Week 1 CLI, same output format with "📋 Câu trả lời:" and "📎 Nguồn:" sections.

### Implementation for User Story 3

- [x] T014 [US3] Modify `src/rag/qa/pipeline.py` to delegate to `src/agents/pipeline.ask_langgraph()` per contract `cli-ask-v2.md` — import `ask_langgraph` from `src.agents.pipeline`, forward `question_text` and `top_k` params, return the resulting `Answer` object unchanged.
- [x] T015 [US3] Verify `src/cli.py` requires NO changes — confirm it still imports `ask` from `src.rag.qa.pipeline` and output formatting remains unchanged (📋/📎 format).

**Checkpoint**: CLI backward compatibility verified — `python -m src.cli ask` uses the new LangGraph pipeline transparently.

---


## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, error resilience, and validation across all stories

- [x] T019 Add input validation in `src/agents/nodes/supervisor.py` — handle empty strings, special-char-only input (e.g., `!!!@@@`), return user-friendly error messages ("Câu hỏi không hợp lệ", "Vui lòng nhập câu hỏi rõ ràng")
- [x] T020 Add structured logging across all agent nodes — log node entry/exit, state transitions, timing, and errors using Python `logging` module for debugging
- [x] T021 [P] Add error resilience for LLM API failures — handle rate-limit and timeout in harm_assessment, rag_agent, and response_agent nodes with fallback error messages per FR-007
- [ ] T022 [P] Update project documentation — add LangGraph architecture notes to README or docs/, update quickstart.md with Phase 1/Phase 2 switching instructions
- [ ] T023 Run quickstart.md validation scenarios end-to-end — execute all 6 scenarios (happy path, prescription refusal, emergency refusal, backward compatibility, evaluation suite, edge cases) and verify expected outputs

---


### Within Each User Story

- State definitions before node implementations
- Node implementations before graph assembly
- Graph assembly before pipeline entry point
- Pipeline entry before CLI integration

### Parallel Opportunities

- T001 and T002 can run in parallel (Setup phase)
- T003 and T004 can run in parallel (Foundational phase — different files)
- T005, T006, T007, T008 can run in parallel within US1 (different node files, all depend only on `AgentState`)
- T011, T012, T013 can run in parallel within US2 (different files/concerns)
- T019, T020, T021, T022 can run in parallel (Polish phase — different files/concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all agent node implementations together (after `AgentState` is defined):
Task: "Implement Supervisor Agent node in src/agents/nodes/supervisor.py"       # T005
Task: "Implement Harm Assessment Agent node in src/agents/nodes/harm_assessment.py"  # T006
Task: "Implement RAG Agent node in src/agents/nodes/rag_agent.py"              # T007
Task: "Implement Response Agent node in src/agents/nodes/response_agent.py"    # T008

# Then sequentially:
Task: "Build StateGraph and compile in src/agents/graph.py"                    # T009
Task: "Implement entry point ask_langgraph() in src/agents/pipeline.py"        # T010
```
---

