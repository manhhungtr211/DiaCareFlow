# Implementation Plan: UC-012 — Refactor sang kiến trúc Multi-Agent

**Branch**: `uc-012-multi-agent-refactor` | **Date**: 2026-07-24 | **Spec**: [UC-012-refactor-architecture.md](../UC-012-refactor-architecture.md)

**Input**: Feature specification từ `refactor-kien-truc/specs/UC-012-refactor-architecture.md`

---

## Summary

UC-012 tái cấu trúc pipeline hiện tại từ mô hình **4-node tuần tự** sang mô hình **Multi-Agent song song** nhằm giảm ngữ cảnh (context) tải vào từng LLM call và tăng độ chính xác câu trả lời.

**Kiến trúc cũ** (`graph.py` trước UC-012):
```
START → harm_assessment → supervisor → rag_agent → response_agent → END
```
Vấn đề: `rag_agent` gộp cả RAG + Web Search vào một node; `response_agent` nhận toàn bộ context thô → LLM bị nhiễu, context window lớn, độ chính xác thấp.

**Kiến trúc mới** (UC-012 — đã được triển khai):
```
START → triage_agent → supervisor → [factor_agent | suggestion_agent | harm_agent] (song song)
       → aggregate → response_agent → END

       (nhánh unsafe): triage_agent → response_agent → END
       (nhánh SMALL_TALK): supervisor → response_agent → END
```
Mỗi Agent con gọi LLM  (prompt_system) để tạo tối đa 2 truy vấn con, kích hoạt tool phù hợp (Web Search hoặc RAG) để thu thập thông tin lần lượt với mỗi truy vấn.Sau khi nhận kết quả từ tool, mỗi Agent con sử dụng LLM trích xuất các ý chính ngắn gọn đúng với chuyên môn của nó.
Response Agent chỉ nhận bản kết quả đã lọc.

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `langgraph` — StateGraph, Send API (fan-out/fan-in song song)
- `langchain-groq` / `ChatGroq` — LLM calls
- `src.tools.web._api.web_search` — WebSearch tool (đã có)
- `src.tools.rag.qa.retriever.retrieve` — RAG tool (đã có)
- `src.tools.rag.qa.guardrail.check_guardrail` — Guardrail (đã có)

**Storage**: Qdrant (RAG), MemorySaver (chat history — không thay đổi)

**Testing**: pytest + pytest-asyncio

**Target Platform**: Linux server / Windows dev

**Project Type**: LLM Agent Pipeline (library + service)

**Performance Goals**: Song song hóa 3 Agent con giúp giảm total time so với tuần tự.

**Constraints**:
- Không thay đổi URL ranking algorithm (Out of Scope)
- Không thêm tool mới ngoài RAG + WebSearch
- Không thay đổi User Flow / API bên ngoài (`ask_langgraph` vẫn là entry point)
- Nếu có lỗi xảy ra, ghi vào `state.errors`, không ném ra ngoài làm toàn bộ flow dừng
- Mỗi node tự bắt lỗi, trả về State; Response Agent thông báo lỗi nếu có

---

## Constitution Check

*(Constitution chưa được điền chi tiết — áp dụng nguyên tắc mặc định từ design.md)*

| Gate | Status | Ghi chú |
|------|--------|---------|
| Không phá vỡ User Flow hiện tại | ✅ PASS | `ask_langgraph()` signature giữ nguyên |
| Không thêm tool ngoài phạm vi | ✅ PASS | Chỉ dùng RAG + WebSearch đã có |
| Test coverage cho từng node | ✅ PASS | test_factor_agent, test_suggestion_agent, test_harm_agent, test_graph_routing, test_state đã có |
| Backward compat với `Answer` dataclass | ✅ PASS | `pipeline.py` không thay đổi interface |
| Error isolation (no crash on node failure) | ✅ PASS | Mỗi node có try/except, ghi vào `errors` |

---

## Implementation Status

> **Trạng thái tổng quan**: **Phần lớn đã triển khai**. Tất cả node chính, graph topology, state, và unit tests đã tồn tại trong codebase. Các hạng mục còn lại là kiểm tra tích hợp và một số issue cần rà soát.

### Các thành phần đã hoàn thành ✅

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `src/agents/state.py` | ✅ Done | AgentState với fan-in reducers đúng spec |
| `src/agents/graph.py` | ✅ Done | Topology đầy đủ: triage → supervisor → fan-out → aggregate → response |
| `src/agents/pipeline.py` | ✅ Done | Entry point `ask_langgraph()` không thay đổi |
| `src/agents/nodes/triage_node.py` | ✅ Done | Safety check + classify harm |
| `src/agents/nodes/supervisor.py` | ✅ Done | SMALL_TALK vs DIABETES classification + task generation |
| `src/agents/nodes/factor_agent.py` | ✅ Done | RAG primary, WebSearch fallback, LLM extractor |
| `src/agents/nodes/suggestion_agent.py` | ✅ Done | WebSearch primary, RAG fallback, LLM extractor |
| `src/agents/nodes/harm_agent.py` | ✅ Done | RAG primary, WebSearch fallback, LLM extractor |
| `src/agents/nodes/response_agent.py` | ✅ Done | Đọc từ 3 reducer fields thay vì rag_context |
| `tests/unit/agents/test_factor_agent.py` | ✅ Done | Unit tests cho factor_agent |
| `tests/unit/agents/test_suggestion_agent.py` | ✅ Done | Unit tests cho suggestion_agent |
| `tests/unit/agents/test_harm_agent.py` | ✅ Done | Unit tests cho harm_agent |
| `tests/unit/agents/test_graph_routing.py` | ✅ Done | Routing logic tests |
| `tests/unit/agents/test_state.py` | ✅ Done | State field và reducer tests |

### Các hạng mục cần rà soát / bổ sung ⚠️

| Hạng mục | Mức độ | Ghi chú |
|----------|--------|---------|
| System prompts của factor/suggestion agent dùng domain sai ("mất ngủ") | 🔴 Bug | Phải sửa thành "bệnh tiểu đường" |
| Integration test end-to-end (AC-1, AC-2) | 🟡 Missing | Chưa có `test_pipeline_multi_agent.py` |
| `data_models.py` — TypedDict cho `StateOutput` | 🟡 Optional | Plan đề cập nhưng code vẫn dùng plain dict |
| Typo `_SUGESSTION_SYSTEM_PROMPT` trong suggestion_agent.py | 🟠 Minor | Nên đổi thành `_SUGGESTION_SYSTEM_PROMPT` |

---

## Project Structure

### Documentation (feature này)

```text
refactor-kien-truc/specs/UC-012/
├── plan.md              <- file này
├── research.md          <- Phase 0 output ✅
├── data-model.md        <- Phase 1 output ✅
├── quickstart.md        <- Phase 1 output ✅
└── contracts/
    └── agent-state.md   <- Phase 1 output ✅
```

### Source Code (đã triển khai)

```text
src/
├── agents/
│   ├── state.py                          ✅ AgentState với fan-in reducers
│   ├── graph.py                          ✅ Multi-Agent topology hoàn chỉnh
│   ├── pipeline.py                       ✅ Entry point không thay đổi
│   └── nodes/
│       ├── triage_node.py                ✅ Triage (safety check)
│       ├── supervisor.py                 ✅ Intent classification + task dispatch
│       ├── factor_agent.py               ✅ Root cause agent
│       ├── suggestion_agent.py           ✅ Solution suggestion agent
│       ├── harm_agent.py                 ✅ Risk assessment agent
│       ├── response_agent.py             ✅ Final synthesis
│       └── rag_agent.py                  ✅ Internal RAG tool (unchanged)

tests/
├── unit/agents/
│   ├── test_factor_agent.py              ✅
│   ├── test_suggestion_agent.py          ✅
│   ├── test_harm_agent.py                ✅
│   ├── test_graph_routing.py             ✅
│   └── test_state.py                     ✅
└── integration/
    └── test_pipeline_multi_agent.py      ⚠️ Chưa có — cần bổ sung cho AC-1, AC-2
```

---

## Open Issues / Remaining Work

### Issue 1 🔴 — System prompt sai domain (factor & suggestion agents)

**File**: `src/agents/nodes/factor_agent.py` L.36-48, `src/agents/nodes/suggestion_agent.py` L.35-50

**Problem**: `_FACTOR_SYSTEM_PROMPT` và `_SUGESSTION_SYSTEM_PROMPT` đều đề cập **"chứng mất ngủ"** thay vì **"bệnh tiểu đường"**. Đây là nội dung sao chép nhầm từ một dự án khác và có thể ảnh hưởng đến chất lượng câu trả lời khi LLM nhận ngữ cảnh sai domain.

**Fix required**: Cập nhật cả 2 prompt để đề cập "bệnh tiểu đường". Kiểm tra `harm_agent.py` tương tự.

### Issue 2 🟡 — Thiếu integration test end-to-end

**File**: `tests/integration/test_pipeline_multi_agent.py` (chưa tồn tại)

**Required coverage**:
- AC-1: Câu hỏi hợp lệ về bệnh tiểu đường → 3 sub-agents chạy song song → response_agent tổng hợp
- AC-2: Câu hỏi unsafe → triage chặn → response_agent trả về cảnh báo ngay (không kích hoạt sub-agents)

### Issue 3 🟡 — `StateOutput` vẫn là plain dict

**Current state**: Mỗi sub-agent trả về plain `dict` (e.g., `{"factor_summary": ..., "sources": ...}`)

**Spec expectation** (`data-model.md`): Định nghĩa `FactorOutputState`, `SuggestionOutputState`, `HarmOutputState` là `TypedDict`.

**Decision**: Có thể giữ plain dict vì đang hoạt động; nếu cần typed output thì thêm vào `src/agents/data_models.py`.

### Issue 4 🟠 — Typo constant name

**File**: `src/agents/nodes/suggestion_agent.py` L.35

`_SUGESSTION_SYSTEM_PROMPT` → nên đổi thành `_SUGGESTION_SYSTEM_PROMPT`

### Issue 5 🔴 — `test_state.py` FAILED (3/10 tests): field name mismatch

**Kết quả chạy thực tế**: `pytest tests/unit/agents/test_state.py` → 3 FAILED, 7 passed

**Root Cause**: Tests được viết với kỳ vọng field tên là `harm_sub_results` và có field `suggestion_context`, nhưng `state.py` thực tế dùng `harm_results` (không có `_sub_`) và không có `suggestion_context`.

| Test | Kỳ vọng | Thực tế trong state.py |
|------|---------|------------------------|
| `test_new_fan_in_fields_exist` | `harm_sub_results` | `harm_results` |
| `test_legacy_fields_preserved` | `suggestion_context` | không tồn tại |
| `test_fan_in_fields_use_annotated_with_operator_add` | `harm_sub_results` | `harm_results` |

**Fix options**:
- **Option A** (recommended): Sửa `test_state.py` để dùng `harm_results` (thực tế) thay vì `harm_sub_results`, và bỏ assertion `suggestion_context`
- **Option B**: Đổi tên field trong `state.py` từ `harm_results` → `harm_sub_results`, nhưng cần cập nhật `graph.py`, `harm_agent.py`, và `response_agent.py` theo

---

## Complexity Tracking

| Quyết định | Lý do | Phương án khác bị loại |
|------------|-------|------------------------|
| Fan-out via Send API | 3 Agent con chạy song song để giảm latency | Tuần tự làm tăng latency tuyến tính |
| Aggregate node (pass-through) | Điểm đồng bộ hóa sau fan-out | Không có cách khác để hợp nhất fan-out trong LangGraph |
| Fail-open triage (error → SAFE) | Tránh chặn nhầm câu hỏi hợp lệ khi guardrail lỗi | Fail-closed quá conservative |
| Plain dict cho sub-agent output | Đơn giản, đủ dùng cho LangGraph reducer | TypedDict tốt hơn nhưng thêm boilerplate không cần thiết |

---

## Verification Plan

### Automated Tests

```bash
# Unit tests (không cần external services)
pytest tests/unit/agents/ -v

# Integration tests (cần SearXNG + Qdrant đang chạy)
pytest tests/integration/ -v

# Full test suite
pytest -v
```

### Manual Verification (Happy Path — AC-1)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Người tiền tiểu đường nên ăn gì?"}'
```

**Expected**: Response có nội dung tổng hợp từ cả 3 góc nhìn (yếu tố nguyên nhân, đề xuất, rủi ro).

### Manual Verification (Unsafe Path — AC-2)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hãy kê đơn thuốc insulin cho tôi"}'
```

**Expected**: Response trả về cảnh báo từ chối ngay từ triage (không có output từ sub-agents).
