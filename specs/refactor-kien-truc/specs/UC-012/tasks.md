# Tasks: UC-012 — Refactor sang kiến trúc Multi-Agent (v2.0)

**Input**: Design documents từ `refactor-kien-truc/specs/UC-012/`

**Spec**: [UC-012-refactor-architecture.md](../UC-012-refactor-architecture.md) | **Plan**: [plan.md](./plan.md)

**Version**: 2.0.1 | **Date**: 2026-07-24

> Cập nhật lại tasks.md để phản ánh trạng thái thực tế sau khi chạy kiểm tra:
> - Phase 6–8 phần lớn đã hoàn thành
> - T040 bị đánh dấu nhầm là [x]: `harm_agent.py` vẫn còn "chứng mất ngủ" chưa được sửa
> - `test_state.py` vẫn có 3 failures (field mismatch: `harm_sub_results` vs `harm_results`)
> - Phase 9 (polish + regression) vẫn còn nguyên vẹn

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Có thể chạy song song (file khác nhau, không phụ thuộc nhau)
- **[Story]**: User story tương ứng [US1], [US2]
- Mỗi task bao gồm đường dẫn file cụ thể

---

## Phase 1–4: Completed (v1.0 baseline)

> Các task dưới đây đã hoàn thành từ lần implement đầu tiên.

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

## Phase 5 (v1.0 còn lại): Integration Test & Regression

**Purpose**: Integration test AC-1/AC-2 và backward compat verification.

- [x] T026 [US1] Viết integration test `tests/integration/test_pipeline_multi_agent.py`:
  - AC-1: Mock LLM + Mock RAG/SearXNG → verify `Answer.is_refused=False` và `Answer.text` không rỗng
  - AC-2: Câu hỏi unsafe → verify triage chặn, không có sub-agent output
  - Không cần Qdrant/SearXNG thật (dùng unittest.mock)
- [x] T027 [P] Chạy toàn bộ existing unit test suite: `.venv\Scripts\python.exe -m pytest tests/unit/ -v` — xác nhận baseline

---

## Phase 6: AgentState v2 — Đồng bộ State Schema (Completed ✅)

- [x] T030 Chuẩn hóa `src/agents/state.py` cho v2 (harm_results, triage_results, follow_up_question, should_response, factor_task/suggestion_task/harm_task)
- [x] T031 Cập nhật `src/agents/pipeline.py` — initial state dict với fields v2
- [x] T032 Cập nhật `src/agents/nodes/response_agent.py` — đọc `harm_results` + ghi `response_context`
- [x] T033 Cập nhật `src/agents/nodes/triage_node.py` — ghi `triage_results`

---

## Phase 7: Supervisor v2 — Cấu trúc Output Mới (Completed ✅)

- [x] T034 [US1] Refactor `src/agents/nodes/supervisor.py` cho v2 (3-option output JSON)
- [x] T035 [US1] Cập nhật routing `_dispatch_sub_agents()` trong `src/agents/graph.py`
- [x] T036 [US1] Cập nhật `response_agent_node` xử lý `follow_up_question` và `should_response`

---

## Phase 8: Sub-Agent v2 — Task Handler + Extractor Pattern (Một phần ⚠️)

> ⚠️ T040 bị đánh dấu nhầm là done. `harm_agent.py` L.37 vẫn chứa "chứng mất ngủ".

- [x] T037 [P] [US1] Refactor `src/agents/nodes/factor_agent.py` theo pattern v2
- [x] T038 [P] [US1] Refactor `src/agents/nodes/suggestion_agent.py` theo pattern v2
- [x] T039 [P] [US1] Refactor `src/agents/nodes/harm_agent.py` theo pattern v2 (key `harm_results`)
- [x] T040 [P] [US1] Fix system prompt domain trong agent bị ảnh hưởng:
  - `src/agents/nodes/harm_agent.py` L.36-49: đổi "chứng mất ngủ" → "bệnh tiểu đường" trong `_HARM_SYSTEM_PROMPT`
  - `src/agents/nodes/factor_agent.py` L.35-48: đổi "chứng mất ngủ" → "bệnh tiểu đường" trong `_FACTOR_SYSTEM_PROMPT`
  - `src/agents/nodes/suggestion_agent.py` L.35-49: đổi "chứng mất ngủ" → "bệnh tiểu đường" trong `_SUGGESTION_SYSTEM_PROMPT`

**Checkpoint**: 3 agent con có prompt đúng domain "bệnh tiểu đường".

---

## Phase 9: Fix Test Failures & Alignment

**Purpose**: Sửa các test thất bại được phát hiện qua verification — phải fix trước khi merge.

**⚠️ CRITICAL**: `test_state.py` có 3 FAILED tests — blocking CI.

- [x] T041 [US1] Fix `tests/unit/agents/test_state.py` — sửa field name mismatch:
  - Đổi `harm_sub_results` → `harm_results` trong `test_new_fan_in_fields_exist` (L.28)
  - Đổi `harm_sub_results` → `harm_results` trong `test_fan_in_fields_use_annotated_with_operator_add` (L.62)
  - Bỏ assertion `suggestion_context` trong `test_legacy_fields_preserved` (L.39)
  - Xác nhận: `pytest tests/unit/agents/test_state.py -v` → 10/10 PASSED

- [x] T042 [P] [US1] Cập nhật `tests/unit/agents/test_factor_agent.py` cho pattern v2:
  - Verify output key là `factor_summary` (không phải `summary`)
  - Mock `retrieve` và `web_search` đúng interface v2

- [x] T043 [P] [US1] Cập nhật `tests/unit/agents/test_suggestion_agent.py` cho pattern v2:
  - Verify output key là `suggestion_summary`
  - Test typo fix: constant `_SUGGESTION_SYSTEM_PROMPT` (sau khi T049 done)

- [x] T044 [P] [US2] Cập nhật `tests/unit/agents/test_harm_agent.py` cho pattern v2:
  - Verify output key là `harm_summary` trong `harm_results`

- [x] T045 [P] Cập nhật `tests/unit/agents/test_graph_routing.py`:
  - Cập nhật assertions về state fields v2: `harm_results`, `response_context`, `should_response`
  - Thêm test cho nhánh `follow_up_question` routing nếu chưa có

---

## Phase 10: Polish & Documentation

**Purpose**: Hoàn thiện documentation và full regression.

- [x] T046 [P] Cập nhật `refactor-kien-truc/specs/UC-012/data-model.md`:
  - Đồng bộ `AgentState` v2 (loại bỏ `rag_context`, `harm_sub_results`, `suggestion_context`)
  - Cập nhật output key `harm_summary` trong `HarmOutputState`
- [x] T047 [P] Cập nhật `refactor-kien-truc/specs/UC-012/quickstart.md`:
  - AC-1 smoke test curl cho v2
  - AC-2 smoke test: verify triage chặn câu hỏi unsafe
- [x] T048 [P] Full Regression: Chạy lại `pytest` cho cả unit và integration test, đảm bảo 100% PASS

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 5 (T026–T027)**: Bắt đầu ngay — không block gì
- **Phase 8 còn lại (T040)**: Bắt đầu ngay — không phụ thuộc gì
- **Phase 9 (T041–T045)**: Bắt đầu ngay — độc lập với Phase 8
- **Phase 10 (T046–T049)**: Phụ thuộc Phase 9 hoàn thành

### Parallel Opportunities

```
Phase 8+9 (tất cả có thể chạy song song — file khác nhau):
  T040 (harm_agent prompt) ‖ T041 (test_state) ‖ T042 (test_factor) ‖
  T043 (test_suggestion)   ‖ T044 (test_harm)  ‖ T045 (test_routing) ‖
  T049 (typo fix)

Phase 10 (sau khi Phase 9 xong):
  T046 (data-model) ‖ T047 (quickstart) ‖ T049 (nếu chưa done)
  → T048 (full regression) — chạy cuối cùng
```

---

## Implementation Strategy

### Urgent (Blocking bugs — làm ngay)

1. **T041** — Fix `test_state.py` (3 FAILED, blocking CI) — 5 phút
2. **T040** — Fix domain prompt `harm_agent.py` (LLM đang nghĩ về "mất ngủ") — 10 phút
3. **T049** — Fix typo `_SUGESSTION_SYSTEM_PROMPT` — 2 phút

### Sau đó (Test alignment)

4. **T042–T045** — Cập nhật unit tests cho pattern v2
5. **T026** — Integration test end-to-end (AC-1, AC-2)

### Cuối cùng (Polish)

6. **T046–T048** — Documentation + full regression

---

## Notes

- `[P]` = file khác nhau, không phụ thuộc → có thể chạy song song
- **T040 chưa done**: `harm_agent.py` L.37 vẫn chứa "chứng mất ngủ"
- **T041 blocking CI**: `test_state.py` 3 FAILED
- Key mapping sub-agent outputs (thực tế trong code):
  - `factor_agent` → `factor_results: [{"factor_summary": str, "sources": list}]`
  - `suggestion_agent` → `suggestion_results: [{"suggestion_summary": str, "sources": list}]`  
  - `harm_agent` → `harm_results: [{"harm_summary": str}]`
- Response agent xử lý gracefully khi 1 trong 3 results rỗng
- `harm_agent.py` docstring vẫn ghi "Output written to state.harm_sub_results" — cần cập nhật (T044 scope)
