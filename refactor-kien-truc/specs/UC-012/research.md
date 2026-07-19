# Research: UC-012 — Multi-Agent Refactor

**Date**: 2026-07-17 | **Feature**: UC-012

---

## 1. LangGraph Fan-out / Fan-in (Send API)

**Decision**: Dùng `langgraph.types.Send` để fan-out sang 3 Agent con, dùng `Annotated[list, operator.add]` để fan-in.

**Rationale**: LangGraph hỗ trợ native parallelism qua `Send` API kể từ v0.1.x. Đây là pattern chính thức để phân tán task sang nhiều sub-node và collect kết quả.

**Pattern**:
```python
from langgraph.types import Send

def dispatch_sub_agents(state: AgentState):
    return [
        Send("factor_agent",    {"user_input": state["user_input"], ...}),
        Send("suggestion_agent", {"user_input": state["user_input"], ...}),
        Send("harm_sub_agent",  {"user_input": state["user_input"], ...}),
    ]

graph.add_conditional_edges("supervisor", dispatch_sub_agents, ["factor_agent", "suggestion_agent", "harm_sub_agent"])
```

**Fan-in**: Mỗi sub-agent ghi vào field `Annotated[list[str], operator.add]` → tự động merge.

**Alternatives considered**:
- `asyncio.gather()` trực tiếp trong một node: Không dùng vì vi phạm nguyên tắc LangGraph (node phải pure function, không spawn coroutine bên trong)
- LangGraph subgraph: Overkill cho 3 agent con đơn giản

---

## 2. State Design cho Multi-Agent Song Song

**Decision**: Thêm 3 field `Annotated[list, operator.add]` vào `AgentState` để thu thập output từ sub-agents.

**Rationale**: `operator.add` reducer cho phép nhiều node ghi vào cùng field mà không bị ghi đè — kết quả được append.

**Fields mới**:
```python
factor_results:     Annotated[list[dict], operator.add]   # output của Factor Agent
suggestion_results: Annotated[list[dict], operator.add]   # output của Suggestion Agent
harm_sub_results:   Annotated[list[dict], operator.add]   # output của Harm Sub Agent
errors:             Annotated[list[str], operator.add]      # lỗi trong quá trình xử lý
```

**Alternatives considered**:
- Dict keyed by agent name: Không hỗ trợ reduce tự động, cần custom reducer
- Separate states per sub-agent (subgraph): Phức tạp hơn cần thiết

---

## 3. Role của từng Agent con

**Decision**: Mỗi Agent con có prompt chuyên biệt, gọi tối đa 1 LLM call, tự quyết định dùng RAG hay WebSearch.

| Agent | Role | Tool ưu tiên | Output |
|-------|------|-------------|--------|
| Factor Agent | Phân tích nguyên nhân/cơ chế y khoa | RAG (tài liệu chuyên sâu) | `{"factor_summary": "..."}` |
| Suggestion Agent | Đề xuất giải pháp thực tế | WebSearch (thông tin cập nhật) + RAG | `{"suggestion_summary": "..."}` |
| Harm Sub Agent | Đánh giá rủi ro / cảnh báo | RAG (guideline y tế) | `{"harm_summary": "..."}` |

**Rationale**: Mỗi Agent chỉ cần context nhỏ và focused → LLM ít bị nhiễu → câu trả lời chính xác hơn. Đây là nguyên tắc "Single Responsibility" cho AI Agent.

**Alternatives considered**:
- Để 1 Agent làm tất cả: Đây là vấn đề hiện tại cần giải quyết
---

## 4. Triage Agent vs Harm Assessment hiện tại

**Decision**: Giữ nguyên `harm_assessment_node` nhưng đổi tên thành `triage_agent` trong graph. Không thay đổi logic bên trong.

**Rationale**: UC-012 đổi tên logic node nhưng không thay đổi behavior của safety check. Đây là rename thuần túy trong `graph.py`.

**Alternatives considered**:
- Tạo file mới `triage_agent.py`: Không cần thiết, thêm code trùng lặp

---

## 5. Supervisor Agent — Đổi role

**Decision**: Supervisor mới không còn classify intent (SMALL_TALK/DIABETES). Thay vào đó:
1. Nhận câu hỏi đã được Triage Agent xác nhận an toàn
2. Dispatch sang 3 Agent con song song qua `Send`

**Rationale**: Intent classification không còn cần thiết khi có Triage Agent làm nhiệm vụ sàng lọc đầu vào. Supervisor chỉ cần làm 1 việc: fan-out.

> **OPEN QUESTION cho user**: SMALL_TALK bypass hiện tại (supervisor → response_agent trực tiếp khi intent = SMALL_TALK) có còn cần thiết trong kiến trúc mới không? Nếu cần, nên để Triage Agent detect SMALL_TALK hay giữ lại ở Supervisor?
SMALL_TALK sẽ được phân loại Supervisor Agent, nếu là SMALL_TALK, sẽ trả lời trực tiếp ra Response Agent, nếu không là SMALL_TALK thì Supervisor Agent sẽ dispatch sang 3 Agent con song song qua `Send`.
---

## 6. Response Agent — Nhận context mới

**Decision**: Response Agent nhận `factor_results`, `suggestion_results`, `harm_sub_results` thay vì `rag_context` thô.

**Rationale**: Mỗi result đã được Agent con tóm tắt → Response Agent prompt nhỏ hơn → ít nhiễu hơn.

**Format input**:
```python
# state.factor_results = [{"factor_summary": "Tiểu đường type 2 do..."}]
# state.suggestion_results = [{"suggestion_summary": "Nên ăn..."}]
# state.harm_sub_results = [{"harm_summary": "Cẩn thận với..."}]
```

---

## 7. Backward Compatibility

**Decision**: `pipeline.py::ask_langgraph()` và `Answer` dataclass không thay đổi.

**Rationale**: Out-of-scope theo spec. Không phá vỡ User Flow.

**Impact**: `_state_to_answer()` cần đọc từ `suggestion_context` như hiện tại — Response Agent mới vẫn ghi vào `suggestion_context`.

---

## Resolved Clarifications

| # | Vấn đề | Quyết định |
|---|--------|-----------|
| 1 | Fan-out mechanism | `Send` API của LangGraph |
| 2 | State reducer | `Annotated[list, operator.add]` |
| 3 | Sub-agent tool selection | Tự quyết định trong prompt |
| 4 | Triage vs Harm Assessment | Rename, giữ logic |
| 5 | SMALL_TALK handling | OPEN (xem section 5) |
