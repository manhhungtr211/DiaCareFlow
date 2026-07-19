# Implementation Plan: UC-012 — Refactor sang kiến trúc Multi-Agent

**Branch**: `uc-012-multi-agent-refactor` | **Date**: 2026-07-17 | **Spec**: [UC-012-refactor-architecture.md](../UC-012-refactor-architecture.md)

**Input**: Feature specification từ `refactor-kien-truc/specs/UC-012-refactor-architecture.md`

---

## Summary

UC-012 tái cấu trúc pipeline hiện tại từ mô hình **4-node tuần tự** sang mô hình **Multi-Agent song song** nhằm giảm ngữ cảnh (context) tải vào từng LLM call và tăng độ chính xác câu trả lời.

**Kiến trúc hiện tại** (`graph.py`):
```
START → harm_assessment → supervisor → rag_agent → response_agent → END
```
Vấn đề: `rag_agent` gộp cả RAG + Web Search vào một node; `response_agent` nhận toàn bộ context thô → LLM bị nhiễu, context window lớn, độ chính xác thấp.

**Kiến trúc mới** (UC-012):
```
START → triage_agent → supervisor_agent → [factor | suggestion | harm_assess_sub] (song song)
       → aggregate → response_agent → END

       (nhánh unsafe): triage_agent → response_agent → END
```
Mỗi Agent con (Factor, Suggestion, Harm Assessment Sub) tự chọn tool (RAG và/hoặc WebSearch), gọi LLM với prompt nhỏ, rồi trả về những ý chính đúng với chức năng của Agent đó. Response Agent chỉ nhận bản kết quả đã được lọc, tạo câu trả lời cuối cùng.

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `langgraph` — StateGraph, Send API (fan-out/fan-in song song)
- `langchain-groq` / `ChatGroq` — LLM calls
- `src.tools.web._api.web_search` — WebSearch tool (UC-011, đã có)
- `src.rag.qa.retriever.retrieve` — RAG tool (đã có)
- `src.rag.qa.guardrail.check_guardrail` — Guardrail (đã có)

**Storage**: Qdrant (RAG), MemorySaver (chat history — không thay đổi)

**Testing**: pytest + pytest-asyncio

**Target Platform**: Linux server / Windows dev

**Project Type**: LLM Agent Pipeline (library + service)

**Performance Goals**: Không tăng latency so với baseline; song song hóa 3 Agent con giúp giảm total time.

**Constraints**:
- Không thay đổi URL ranking algorithm (Out of Scope)
- Không thêm tool mới ngoài RAG + WebSearch
- Không thay đổi User Flow / API bên ngoài (`ask_langgraph` vẫn là entry point)
- Nếu có lỗi xảy ra, cần ghi lại vào `state.errors`, không ném ra ngoài luôn làm toàn bộ flow dừng, mỗi node sẽ tự bắt lỗi, trả về State , Response sẽ thông báo lỗi (néu có)
**Scale/Scope**: Cùng tập test characterization với UC-011; 100% pass rate yêu cầu.

---

## Constitution Check

*(Constitution chưa được điền chi tiết — áp dụng các nguyên tắc mặc định)*

| Gate | Status | Ghi chú |
|------|--------|---------|
| Không phá vỡ User Flow hiện tại | PASS | `ask_langgraph()` signature giữ nguyên |
| Không thêm tool ngoài phạm vi | PASS | Chỉ dùng RAG + WebSearch đã có |
| Test coverage cho từng node | REQUIRED | Mỗi Agent con cần unit test riêng |
| Backward compat với `Answer` dataclass | PASS | `pipeline.py` không thay đổi interface |

---

## Project Structure

### Documentation (this feature)

```text
refactor-kien-truc/specs/UC-012/
├── plan.md              <- file này
├── research.md          <- Phase 0 output
├── data-model.md        <- Phase 1 output
├── quickstart.md        <- Phase 1 output
└── contracts/
    └── agent-state.md   <- Phase 1 output
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── state.py                        <- [MODIFY] thêm fields mới
│   ├── graph.py                        <- [MODIFY] topology mới
│   ├── pipeline.py                     <- [NO CHANGE] entry point giữ nguyên
│   └── nodes/
│       ├── harm_assessment.py          <- [RENAME/REUSE] trở thành Triage Agent
│       ├── supervisor.py               <- [MODIFY] đổi role: phân chia task song song
│       ├── rag_agent.py                <- [NO CHANGE] dùng làm internal tool
│       ├── response_agent.py           <- [MODIFY] nhận state tổng hợp mới
│       ├── factor_agent.py             <- [NEW] Agent phân tích nguyên nhân
│       ├── suggestion_agent.py         <- [NEW] Agent đề xuất giải pháp
│       └── harm_sub_agent.py           <- [NEW] Agent đánh giá rủi ro (sub)

tests/
├── unit/
│   └── agents/
│       ├── test_factor_agent.py        <- [NEW]
│       ├── test_suggestion_agent.py    <- [NEW]
│       ├── test_harm_sub_agent.py      <- [NEW]
│       └── test_graph_routing.py       <- [MODIFY]
└── integration/
    └── test_pipeline_multi_agent.py    <- [NEW] end-to-end AC-1, AC-2
```

**Structure Decision**: Option 1 (Single project). Tất cả thay đổi nằm trong `src/agents/` — không tạo package mới.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Fan-out (Send API) | 3 Agent con chạy song song để giảm latency | Tuần tự làm tăng latency tuyến tính |
| Aggregate node mới | Cần gom kết quả từ 3 nhánh song song | Không có cách khác để hợp nhất fan-out trong LangGraph |
