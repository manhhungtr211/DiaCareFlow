# Tasks: UC-012 — Refactor sang kiến trúc Multi-Agent (v2.0)

**Input**: Design documents từ `refactor-kien-truc/specs/UC-012/`

**Spec**: [UC-012-refactor-architecture.md](../UC-012-refactor-architecture.md) | **Plan**: [plan.md](./plan.md)

**Version**: 2.0.0 | **Date**: 2026-07-24

> Cập nhật lại tasks.md để phản ánh các thay đổi kiến trúc v2.0: Supervisor v2 (follow_up, should_response),
> Sub-agent v2 (Task Handler + Extractor pattern), AgentState v2 (đổi tên fields), và các task còn lại từ v1.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Có thể chạy song song (file khác nhau, không phụ thuộc nhau)
- **[Story]**: User story tương ứng [US1], [US2]
- Mỗi task bao gồm đường dẫn file cụ thể

---

## Phase 1–4: Completed (v1.0 baseline)

> Các task dưới đây đã hoàn thành từ lần implement trước.

- [x] T001 Tạo file `src/agents/nodes/factor_agent.py`
- [x] T002 Tạo file `src/agents/nodes/suggestion_agent.py`
- [x] T003 Tạo file `src/agents/nodes/harm_sub_agent.py` (đã đổi tên thực tế là `harm_agent.py`)
- [x] T004 Tạo thư mục `tests/unit/agents/`
- [x] T005 Cập nhật `AgentState` v1 trong `src/agents/state.py`
- [x] T006 Cập nhật initial state trong `src/agents/pipeline.py`
- [x] T007 Đổi tên node `harm_assessment` thành `triage_agent` trong `src/agents/graph.py`
- [x] T008 Unit test `AgentState` schema trong `tests/unit/agents/test_state.py`
- [x] T009 Refactor `supervisor.py` v1 — fan-out sang 3 agent con
- [x] T010 Implement `factor_agent_node` v1
- [x] T011 Implement `suggestion_agent_node` v1
- [x] T012 Implement `harm_agent_node` v1
- [x] T013 Thêm `aggregate_node` vào `src/agents/graph.py`
- [x] T014 Refactor `response_agent.py` v1
- [x] T015 Cập nhật graph topology hoàn chỉnh
- [x] T016 Unit test `test_factor_agent.py`
- [x] T017 Unit test `test_suggestion_agent.py`
- [x] T018 Unit test `test_harm_sub_agent.py`
- [x] T019 Unit test `test_graph_routing.py::test_happy_path_routing`
- [x] T020 Conditional edge `triage_agent → response_agent` (unsafe path)
- [x] T021 Verify `response_agent.py` xử lý đúng unsafe path
- [x] T022 Unit test `test_unsafe_bypasses_sub_agents`
- [x] T023 Unit test `test_smalltalk_bypasses_sub_agents`
- [x] T024 Xóa `rag_context` khỏi `state.py` và `pipeline.py`
- [x] T025 Cập nhật `src/agents/nodes/__init__.py`
- [x] T028 Cập nhật docstring trong `src/agents/graph.py`
- [x] T029 Cập nhật `refactor-kien-truc/design.md`

---

## Phase 5 (v1.0 Còn lại): Polish & Integration Tests

**Purpose**: Dọn dẹp v1, backward compat verification.

- [ ] T026 Viết integration test `tests/integration/test_pipeline_multi_agent.py`: end-to-end AC-1 với mock LLM (không cần Qdrant/SearXNG thật), verify `Answer.is_refused=False` và `Answer.text` không rỗng
- [ ] T027 [P] Chạy toàn bộ existing unit test suite để verify backward compat: `pytest tests/unit/ -v`

---

## Phase 6: AgentState v2 — Đồng bộ State Schema

**Purpose**: Đồng bộ `AgentState` và `pipeline.py` với toàn bộ fields mới đã được thêm vào codebase và data-model.md v2.

**⚠️ CRITICAL**: Các tasks này PHẢI hoàn thành trước Phase 7 vì mọi node đều đọc/ghi state.

- [x] T030 Chuẩn hóa `src/agents/state.py` cho v2:
  - Đổi tên `harm_task: SafetyCategory` → `triage_results: SafetyCategory` (triage output)
  - Đổi `harm_sub_results` → `harm_results` (Annotated list)
  - Đổi `suggestion_context` → `response_context` (Response Agent output)
  - Thêm `follow_up_question: str` (Supervisor v2 output)
  - Thêm `should_response: bool` (Supervisor v2 signal)
  - Thêm `factor_task: str`, `suggestion_task: str`, `harm_task: str` (task strings từ supervisor)
  - Xóa `factor_question`, `suggestion_question`, `harm_question` (đổi thành `*_task`)

- [x] T031 Cập nhật `src/agents/pipeline.py` — initial state dict:
  - Thêm keys mới: `follow_up_question=""`, `should_response=False`, `factor_task=""`, `suggestion_task=""`, `harm_task=""`
  - Đổi key `harm_sub_results` → `harm_results` (init = `[]`)
  - Đổi key `suggestion_context` → `response_context` (init = `{}`)
  - Cập nhật hàm `_state_to_answer()` để đọc từ `response_context` thay vì `suggestion_context`

- [x] T032 Cập nhật `src/agents/nodes/response_agent.py`:
  - Đọc `harm_results` thay vì `harm_sub_results`
  - Ghi `response_context` thay vì `suggestion_context`

- [x] T033 Cập nhật `src/agents/nodes/triage_node.py` (nếu có):
  - Ghi `triage_results` thay vì `harm_task` cho kết quả classification

**Checkpoint**: Tất cả nodes đọc/ghi đúng field names v2. Chạy `pytest tests/unit/ -v` để verify.

---

## Phase 7: Supervisor v2 — Cấu trúc Output Mới

**Purpose**: Supervisor v2 có 3 output options (`follow_up_question`, `should_response`, hoặc fan-out tasks), thay thế logic SMALL_TALK/DIABETES cũ.

**⚠️ Prerequisites**: Phase 6 phải hoàn thành.

- [ ] T034 [US1] Refactor hoàn chỉnh `src/agents/nodes/supervisor.py` cho v2:
  - Viết lại system prompt: Supervisor là orchestrator quyết định 1 trong 3 option:
    1. `follow_up_question`: khi câu hỏi mơ hồ, cần làm rõ
    2. `should_response=True`: khi câu đơn giản (SMALL_TALK, chào hỏi), báo hiệu gọi thẳng response_agent
    3. Fan-out tasks: `factor_task`, `suggestion_task`, `harm_task` → giao việc cho 3 agent con
  - Output JSON schema phải là: `{"follow_up_question": str | null, "should_response": bool | null, "factor_task": str | null, "suggestion_task": str | null, "harm_task": str | null}`
  - Viết lại parser: đọc đúng các fields mới từ JSON response
  - Ghi `follow_up_question`, `should_response` vào state
  - Cập nhật routing: dùng `should_response` thay vì `intent=="SMALL_TALK"` để route thẳng tới `response_agent`

- [ ] T035 [US1] Cập nhật routing function `_dispatch_sub_agents()` trong `src/agents/graph.py`:
  - Kiểm tra `state.get("should_response", False)` → route tới `response_agent`
  - Kiểm tra `state.get("follow_up_question")` → route tới `response_agent` (trả follow_up question luôn)
  - Kiểm tra tasks (`factor_task`, `suggestion_task`, `harm_task`) → fan-out `Send` tới các agent có task
  - Cập nhật `Send` payload: truyền `factor_task`, `suggestion_task`, `harm_task` thay vì `factor_question`, `suggestion_question`, `harm_question`

- [ ] T036 [US1] Cập nhật `response_agent_node` để xử lý `follow_up_question`:
  - Nếu `state.get("follow_up_question")` khác rỗng → trả về follow_up question trực tiếp làm `final_answer`
  - Nếu `state.get("should_response")` là True → generate câu trả lời từ chat_history (không cần sub-agent results)

**Checkpoint**: Supervisor v2 hoàn chỉnh. Smoke test: hỏi "chào bạn" → không gọi sub-agents, trả lời ngay.

---

## Phase 8: Sub-Agent v2 — Task Handler + Extractor Pattern

**Purpose**: Mỗi agent con v2 hoạt động theo pattern 2 bước: (1) Task Handler sinh queries, (2) Extractor trích xuất thông tin từ kết quả tool.

**⚠️ Prerequisites**: Phase 6 phải hoàn thành. Các task này có thể chạy song song nhau.

- [x] T037 [P] [US1] Refactor `src/agents/nodes/factor_agent.py` theo pattern v2:
  - Sửa domain prompt từ "chứng mất ngủ" → "bệnh tiểu đường"
  - Sửa `extractor_prompt` thành f-string với `context_text` được inject
  - Fix `return ""` → `return {"factor_results": [], "nodes_visited": [...]}`

- [x] T038 [P] [US1] Refactor `src/agents/nodes/suggestion_agent.py` theo pattern v2:
  - Sửa typo `_SUGESSTION_SYSTEM_PROMPT` → `_SUGGESTION_SYSTEM_PROMPT`
  - Sửa domain prompt từ "chứng mất ngủ" → "bệnh tiểu đường"
  - Sửa `extractor_prompt` thành f-string với `context_text` được inject
  - Fix `return ""` → `return {"suggestion_results": [], "nodes_visited": [...]}`

- [x] T039 [P] [US1] Refactor `src/agents/nodes/harm_agent.py` theo pattern v2:
  - Sửa domain prompt từ "chứng mất ngủ" → "bệnh tiểu đường"
  - Sửa `extractor_prompt` thành f-string với `context_text` được inject
  - Fix `return ""` → `return {"harm_results": [], "nodes_visited": [...]}`
  - Fix key `harm_sub_results` → `harm_results` trong cả success và error paths

- [x] T040 [US1] Fix system prompt domain trong tất cả 4 agent:
  - `suggestion_agent.py`: Sửa `_SUGESSTION_SYSTEM_PROMPT` (typo + domain)
  - `harm_agent.py`: Sửa `_HARM_SYSTEM_PROMPT` (domain)
  - `factor_agent.py`: Sửa `_FACTOR_SYSTEM_PROMPT` (domain)
  - `response_agent.py`: Sửa `_RESPONSE_SYSTEM_PROMPT` (domain + string format bugs)

**Checkpoint**: 3 agent con hoạt động theo pattern v2. Chạy AC-1 smoke test.

---

## Phase 9: Polish & Regression (v2.0)

**Purpose**: Đảm bảo backward compat, fix lỗi, cập nhật tests.

- [ ] T041 [P] Cập nhật unit tests `tests/unit/agents/test_factor_agent.py`, `test_suggestion_agent.py`, `test_harm_sub_agent.py` để phản ánh pattern v2 (Task Handler + Extractor)
- [ ] T042 [P] Cập nhật unit test `tests/unit/agents/test_graph_routing.py`: cập nhật assertions về state fields v2 (`harm_results`, `response_context`, `should_response`)
- [ ] T043 Chạy toàn bộ test suite: `pytest tests/ -v` — mục tiêu 0 failures
- [ ] T044 [P] Cập nhật `data-model.md` để đồng bộ `AgentState` v2 (loại bỏ fields cũ, cập nhật node contracts phản ánh `harm_results`, `response_context`)
- [ ] T045 Cập nhật `quickstart.md` — AC-1, AC-2 smoke test steps cho v2

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 5**: Có thể bắt đầu ngay (T026, T027 độc lập)
- **Phase 6 (State v2)**: Phụ thuộc Phase 5 checkpoint — **BLOCK Phase 7, 8**
- **Phase 7 (Supervisor v2)**: Phụ thuộc Phase 6
- **Phase 8 (Sub-Agent v2)**: Phụ thuộc Phase 6 — có thể chạy song song với Phase 7
- **Phase 9 (Polish)**: Phụ thuộc Phase 7 + 8

### Trong Phase 8

```
T037, T038, T039 (3 agent refactor) có thể chạy SONG SONG
T040 (fix prompts) có thể chạy song song với T037-T039
```

### Parallel Opportunities

- T037 ‖ T038 ‖ T039 ‖ T040 (Phase 8)
- T041 ‖ T042 ‖ T044 ‖ T045 (Phase 9)
- T026 ‖ T027 (Phase 5)

---

## Implementation Strategy

### Tiếp theo ngay (Urgent Fixes)

1. **T040 (fix prompts)** — Sửa ngay vì bug nghiêm trọng: 4 agents đang có prompt nói về "chứng mất ngủ" thay vì "bệnh tiểu đường"
2. **T038/T039 (fix return `""`)** — `suggestion_agent` và `harm_agent` đang trả về `""` thay vì dict khi không có context → crash pipeline

### Sau đó

3. **Phase 6 (T030–T033)**: Chuẩn hóa state schema v2
4. **Phase 7 (T034–T036)**: Supervisor v2 hoàn chỉnh
5. **Phase 8 (T037–T039)**: Sub-Agent v2 pattern

---

## Notes

- `[P]` = file khác nhau, không phụ thuộc → có thể chạy song song
- **Bug nghiêm trọng**: `suggestion_agent.py` và `harm_agent.py` có `else: return ""` → LangGraph node PHẢI trả về `dict`, trả về `str` sẽ crash graph
- **Bug typo**: `_SUGESSTION_SYSTEM_PROMPT` (thừa chữ 'S') trong `suggestion_agent.py`
- **Wrong domain**: Tất cả system prompt v2 hiện đang nói về "chứng mất ngủ" — cần sửa thành "bệnh tiểu đường"
- Khi sub-agent không có context: trả về `{"*_results": [], "nodes_visited": [...]}` — KHÔNG return `""`
- `response_agent` phải xử lý gracefully khi 1 trong 3 results rỗng
