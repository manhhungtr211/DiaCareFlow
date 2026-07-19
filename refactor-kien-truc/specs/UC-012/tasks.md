# Tasks: UC-012 — Refactor sang kiến trúc Multi-Agent

**Input**: Design documents từ `refactor-kien-truc/specs/UC-012/`

**Spec**: [UC-012-refactor-architecture.md](../UC-012-refactor-architecture.md) | **Plan**: [plan.md](./plan.md)

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Có thể chạy song song (file khác nhau, không phụ thuộc nhau)
- **[Story]**: User story tương ứng [US1], [US2]
- Mỗi task bao gồm đường dẫn file cụ thể

---

## Phase 1: Setup

**Purpose**: Chuẩn bị nền tảng trước khi bắt đầu implement

- [X] T001 Tạo file `src/agents/nodes/factor_agent.py` (stub rỗng với docstring)
- [X] T002 Tạo file `src/agents/nodes/suggestion_agent.py` (stub rỗng với docstring)
- [X] T003 Tạo file `src/agents/nodes/harm_sub_agent.py` (stub rỗng với docstring)
- [X] T004 Tạo thư mục `tests/unit/agents/` nếu chưa tồn tại

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Các thay đổi nền tảng mà MỌI user story đều phụ thuộc vào — phải hoàn thành trước khi implement bất kỳ node nào mới.

**⚠️ CRITICAL**: Không bắt đầu Phase 3/4 cho đến khi Phase 2 hoàn thành.

- [X] T005 Cập nhật `AgentState` trong `src/agents/state.py`: thêm 4 fields mới (`factor_results`, `suggestion_results`, `harm_sub_results`, `errors` với `Annotated[list, operator.add]`); xoá field `rag_context`; giữ nguyên `intent` và `small_talk_reply` cho SMALL_TALK path
- [X] T006 Cập nhật initial state trong `src/agents/pipeline.py`: khởi tạo 4 fields mới = `[]`, xoá `rag_context` khỏi initial state dict
- [X] T007 Đổi tên node `harm_assessment` thành `triage_agent` trong `src/agents/graph.py` (chỉ thay đổi tên đăng ký node, không thay đổi logic `triage_agent_node`)
- [X] T008 [P] Viết unit test cho `AgentState` schema mới trong `tests/unit/agents/test_state.py`: kiểm tra các fields mới tồn tại, reducer `operator.add` hoạt động đúng

**Checkpoint**: `AgentState` mới sẵn sàng, graph đã nhận `triage_agent` — có thể bắt đầu implement nodes mới.

---

## Phase 3: US1 — Happy Path (AC-1) 🎯 MVP

**Goal**: Câu hỏi hợp lệ đi qua toàn bộ pipeline mới: Triage → Supervisor → [Factor | Suggestion | HarmSub] (song song) → Response Agent, trả về câu trả lời dựa trên tài liệu y khoa và web, không tự sáng tạo thông tin.

**Independent Test**:
```bash
pytest tests/unit/agents/test_factor_agent.py -v
pytest tests/unit/agents/test_suggestion_agent.py -v
pytest tests/unit/agents/test_harm_sub_agent.py -v
pytest tests/unit/agents/test_graph_routing.py::TestHappyPathRouting -v
```

### Implementation — Supervisor Agent (đổi role)

- [X] T009 [US1] Refactor `src/agents/nodes/supervisor.py`: bỏ intent classification (SMALL_TALK/DIABETES); đây là bộ não điều khiển chính của LLM, nơi đây sẽ quyết định làm gì tiếp theo, nếu user hỏi câu hỏi không liên quan tới bệnh tiểu đường (VD: chào bạn, bạn khoẻ không...) thì trả về câu trả lời trực tiếp, nếu không thì sẽ phân tách yêu cầu thành các sub-ques phù hợp với các agent con và gửi list `Send` objects fan-out sang 3 agent con (`factor_agent`, `suggestion_agent`, `harm_sub_agent`) theo các câu hỏi tương ứng.

### Implementation — 3 Agent con (song song)

- [X] T010 [P] [US1] Implement `factor_agent_node` trong `src/agents/nodes/factor_agent.py`: nhận `user_input`,trả về nội dung chính về nguyên nhân/cơ chế y khoa (sử dụng tool RAG, web_search nếu cần), ghi `factor_results` và `nodes_visited`; bắt mọi Exception → ghi vào `errors`, trả `factor_results=[]`
- [X] T011 [P] [US1] Implement `suggestion_agent_node` trong `src/agents/nodes/suggestion_agent.py`: nhận `user_input`,trả về nội dung chính về giải pháp thực tế (sử dụng tool RAG, web_search nếu cần), ghi `suggestion_results` và `nodes_visited`; bắt mọi Exception → ghi vào `errors`, trả `suggestion_results=[]`
- [X] T012 [P] [US1] Implement `harm_sub_agent_node` trong `src/agents/nodes/harm_sub_agent.py`: nhận `user_input`,trả về nội dung chính về rủi ro/cảnh báo (sử dụng tool RAG, web_search nếu cần), ghi `harm_sub_results` và `nodes_visited`; bắt mọi Exception → ghi vào `errors`, trả `harm_sub_results=[]`
*Note: Mỗi Agent sử dụng cơ chế để quyết đinh có dùng tool hay ko, hay dùng tool nào: Rag hay web_search hay cả 2
### Implementation — Aggregate Node

- [X] T013 [US1] Thêm `aggregate_node` vào `src/agents/graph.py` (pure function, không gọi LLM): nhận state với 3 result lists đã được fan-in, pass-through không thay đổi state

### Implementation — Response Agent (cập nhật)

- [X] T014 [US1] Refactor `src/agents/nodes/response_agent.py`: bỏ đọc `rag_context`; đọc `factor_results[0]`, `suggestion_results[0]`, `harm_sub_results[0]` thay thế; format prompt tổng hợp từ 3 summaries; gọi `generate()` hoặc gọi LLM trực tiếp; xử lý trường hợp 1 hoặc nhiều sub-agent bị lỗi (dùng empty string nếu list rỗng)

### Implementation — Graph Topology

- [X] T015 [US1] Cập nhật `src/agents/graph.py` topology hoàn chỉnh: (1) `START → triage_agent`; (2) conditional edge `triage_agent` → `supervisor` (safe) hoặc `response_agent` (unsafe); (3) conditional edge `supervisor` → SMALL_TALK path `response_agent` hoặc fan-out `Send` sang 3 agents; (4) `factor_agent`, `suggestion_agent`, `harm_sub_agent` → `aggregate_node`; (5) `aggregate_node → response_agent → END`

### Unit Tests — 3 Agent con

- [X] T016 [P] [US1] Viết unit test `tests/unit/agents/test_factor_agent.py`: mock `retrieve()`, kiểm tra `factor_results` được ghi đúng format, kiểm tra error path ghi vào `errors`
- [X] T017 [P] [US1] Viết unit test `tests/unit/agents/test_suggestion_agent.py`: mock `web_search()`, kiểm tra `suggestion_results` được ghi đúng format, kiểm tra error path
- [X] T018 [P] [US1] Viết unit test `tests/unit/agents/test_harm_sub_agent.py`: mock `retrieve()`, kiểm tra `harm_sub_results` được ghi đúng format, kiểm tra error path
- [X] T019 [US1] Viết unit test `tests/unit/agents/test_graph_routing.py::test_happy_path_routing`: mock tất cả nodes, verify `nodes_visited` chứa `['triage_agent', 'supervisor', 'factor_agent', 'suggestion_agent', 'harm_sub_agent', 'aggregate', 'response_agent']`

**Checkpoint**: Pipeline đầy đủ cho câu hỏi hợp lệ hoạt động end-to-end. Chạy quickstart.md AC-1 smoke test để verify.

---

## Phase 4: US2 — Triage chặn câu hỏi độc hại (AC-2)

**Goal**: Khi Triage Agent phát hiện câu hỏi không an toàn, pipeline bỏ qua toàn bộ sub-agents và tools (RAG/WebSearch), Response Agent trả về cảnh báo ngay lập tức — không tốn thêm token.

**Independent Test**:
```bash
pytest tests/unit/agents/test_graph_routing.py::TestUnsafePathRouting -v
pytest tests/unit/agents/test_graph_routing.py::TestSmallTalkRouting -v
```

### Implementation

- [X] T020 [US2] Cập nhật `src/agents/graph.py` conditional edge sau `triage_agent`: khi `is_safe=False` → route thẳng đến `response_agent`, bỏ qua `supervisor`, 3 agent con, và `aggregate_node`
- [X] T021 [US2] Verify `src/agents/nodes/response_agent.py` xử lý đúng unsafe path: đọc `suggestion_context.refusal_message` khi `is_safe=False`, không đọc `factor_results`/`suggestion_results`/`harm_sub_results`

### Unit Tests

- [X] T022 [US2] Viết unit test `tests/unit/agents/test_graph_routing.py::test_unsafe_bypasses_sub_agents`: mock triage trả `is_safe=False`, verify `factor_agent`, `suggestion_agent`, `harm_sub_agent` KHÔNG được gọi; verify `response_agent` nhận `refusal_message`
- [X] T023 [US2] Viết unit test `tests/unit/agents/test_graph_routing.py::test_smalltalk_bypasses_sub_agents`: mock supervisor trả SMALL_TALK, verify 3 sub-agents KHÔNG được gọi; verify response trả `small_talk_reply`

**Checkpoint**: AC-2 verified. Chạy quickstart.md AC-2 smoke test.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Dọn dẹp, backward compat verification, regression tests.

- [X] T024 [P] Xóa field `rag_context` ra khỏi `src/agents/state.py` (nếu chưa làm ở T005) và cập nhật initial state dict trong `src/agents/pipeline.py`
- [X] T025 [P] Cập nhật `src/agents/nodes/__init__.py`: export `factor_agent_node`, `suggestion_agent_node`, `harm_sub_agent_node`
- [ ] T026 Viết integration test `tests/integration/test_pipeline_multi_agent.py`: end-to-end AC-1 với mock LLM (không cần Qdrant/SearXNG thật), verify `Answer.is_refused=False` và `Answer.text` không rỗng
- [ ] T027 [P] Chạy toàn bộ existing unit test suite để verify backward compat: `pytest tests/unit/ -v --ignore=tests/unit/agents/`
- [X] T028 Cập nhật docstring trong `src/agents/graph.py`: mô tả topology mới (thay thế docstring cũ tham chiếu UC-009/UC-010)
- [X] T029 [P] Cập nhật `refactor-kien-truc/design.md`: bổ sung sơ đồ luồng xử lý chi tiết của hệ thống Multi-Agent mới

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Không phụ thuộc — bắt đầu ngay
- **Phase 2 (Foundational)**: Phụ thuộc Phase 1 — **BLOCK toàn bộ** US1 và US2
- **Phase 3 (US1)**: Phụ thuộc Phase 2 hoàn thành
- **Phase 4 (US2)**: Phụ thuộc T015 (graph topology) — có thể bắt đầu song song với T016-T019
- **Phase 5 (Polish)**: Phụ thuộc Phase 3 + 4 hoàn thành

### Trong Phase 3

```
T009 (Supervisor) phải xong trước T015 (Graph topology)
T010, T011, T012 (3 agent con) có thể chạy SONG SONG với nhau
T013 (Aggregate) có thể chạy song song với T010-T012
T014 (Response Agent) phụ thuộc T010, T011, T012
T015 (Graph) phụ thuộc T009, T013, T014
T016, T017, T018, T019 (unit tests) có thể chạy song song sau T010-T012
```

### Trong Phase 4

```
T020 phụ thuộc T015
T021 phụ thuộc T014
T022, T023 có thể chạy song song sau T020-T021
```

---

## Parallel Example: Phase 3

```bash
# Chạy song song 3 agent con + aggregate:
Task: "Implement factor_agent_node trong src/agents/nodes/factor_agent.py"     [T010]
Task: "Implement suggestion_agent_node trong src/agents/nodes/suggestion_agent.py" [T011]
Task: "Implement harm_sub_agent_node trong src/agents/nodes/harm_sub_agent.py" [T012]
Task: "Thêm aggregate_node vào graph.py"                                        [T013]

# Sau khi T010-T013 xong, chạy song song:
Task: "Unit test factor_agent"    [T016]
Task: "Unit test suggestion_agent" [T017]
Task: "Unit test harm_sub_agent"   [T018]
```

---

## Implementation Strategy

### MVP (Phase 1 + 2 + 3)

1. Complete Phase 1: Setup stubs
2. Complete Phase 2: AgentState + graph rename (CRITICAL)
3. Complete Phase 3: Full US1 happy path pipeline
4. **STOP & VALIDATE**: Chạy AC-1 smoke test từ `quickstart.md`
5. Nếu pass → tiếp tục Phase 4

### Incremental Delivery

1. Phase 1 + 2 → Foundation sẵn sàng
2. Phase 3 → US1 hoàn chỉnh, test AC-1 → MVP!
3. Phase 4 → US2 hoàn chỉnh, test AC-2
4. Phase 5 → Polish, regression, docs

---

## Notes

- `[P]` = file khác nhau, không phụ thuộc → có thể chạy song song
- `suggestion_agent` dùng `asyncio.run(web_search(...))` vì node LangGraph là sync function
- Khi sub-agent lỗi: ghi vào `errors` list (Annotated reducer), KHÔNG raise exception để tránh dừng toàn bộ flow
- `response_agent` phải xử lý gracefully khi 1 trong 3 results rỗng (sub-agent lỗi)
- Commit sau mỗi phase checkpoint
- Verify `ask_langgraph()` signature và `Answer` dataclass không thay đổi (backward compat)
