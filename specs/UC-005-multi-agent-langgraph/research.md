# Research: UC-005 — Multi-Agent Pipeline LangGraph

## Decision 1: LangGraph StateGraph Pattern

**Decision**: Sử dụng `langgraph.graph.StateGraph` với `TypedDict` state schema.

**Rationale**:
- LangGraph là framework chính thức của LangChain cho multi-agent orchestration
- StateGraph cho phép định nghĩa rõ ràng nodes, edges, và conditional routing
- TypedDict state schema đảm bảo type safety cho trạng thái chia sẻ giữa nodes
- Hỗ trợ conditional edges để routing dựa trên kết quả đánh giá an toàn

**Alternatives considered**:
- **LangChain Sequential Chain**: Quá đơn giản, không hỗ trợ conditional routing (skip RAG khi nguy hiểm)
- **Custom orchestration (pure Python)**: Linh hoạt nhưng phải tự implement retry, state management, error handling
- **CrewAI**: Overkill cho usecase này, thêm abstraction không cần thiết

## Decision 2: Agent State Design

**Decision**: Sử dụng một `TypedDict` duy nhất (`AgentState`) chứa toàn bộ trạng thái pipeline.

**Rationale**:
- Mỗi node đọc/ghi vào state dict, không cần truyền tham số phức tạp
- State bao gồm: question, safety_assessment, rag_context, final_answer, metadata (timestamps, nodes_visited)
- Dễ debug vì toàn bộ state có thể serialize ra JSON để log

**Alternatives considered**:
- **Message-based state (LangGraph Messages)**: Phù hợp cho chatbot multi-turn, nhưng pipeline này là single-turn Q&A
- **Pydantic BaseModel state**: Strict hơn nhưng LangGraph recommend TypedDict cho state

## Decision 3: Routing Strategy (Conditional Edges)

**Decision**: Supervisor Agent sử dụng conditional edge dựa trên `safety_assessment` field trong state.

**Routing logic**:
```
Supervisor → Harm Assessment → [conditional]
  - Nếu AN TOÀN → RAG Agent → Response Agent → END
  - Nếu NGUY HIỂM → END (trả câu từ chối từ Harm Assessment)
```

**Rationale**:
- LangGraph conditional edges cho phép routing declarative, dễ đọc
- Supervisor đặt routing decision vào state, Harm Assessment thực hiện đánh giá, conditional edge đọc kết quả
- Không cần agent-to-agent communication phức tạp

**Alternatives considered**:
- **Supervisor gọi trực tiếp các agent**: Không tận dụng được graph-based execution của LangGraph
- **Mỗi agent tự quyết định next step**: Khó kiểm soát flow, dễ xảy ra infinite loop

## Decision 4: Tracer Bullet Strategy (2 Phases)

**Decision**: 
- **Phase 1**: 2 nodes trên LangGraph: `guardrail_node` → `qa_rag_node` (gộp retrieve + generate)
- **Phase 2**: Tách thành 4 nodes: `supervisor` → `harm_assessment` → `rag_agent` → `response_agent`

**Rationale**:
- Phase 1 chứng minh LangGraph pipeline hoạt động end-to-end trên infra hiện tại
- Phase 2 refine bằng cách tách responsibilities rõ ràng
- Cả 2 phases đều expose cùng interface `ask(question) -> Answer`
- Config `LANGGRAPH_PHASE` cho phép chuyển đổi giữa 2 phases mà không đổi code bên ngoài

**Alternatives considered**:
- **Implement thẳng 4 agents**: Rủi ro "Big Bang Integration", khó debug nếu lỗi xảy ra
- **3 agents (skip Supervisor)**: Mất khả năng centralized routing trong tương lai

## Decision 5: Backward Compatibility Strategy

**Decision**: Sửa `src/rag/qa/pipeline.py` để delegate sang `src/agents/pipeline.py`. CLI vẫn import từ `src.rag.qa.pipeline.ask`.

**Rationale**:
- Zero change cho `src/cli.py` — lệnh `python -m src.cli ask` hoạt động y hệt
- Evaluation runner (`src/evaluation/runner.py`) cũng không cần thay đổi vì nó import `ask` từ `src.rag.qa.pipeline`
- Nếu LangGraph gặp lỗi import, có thể fallback về pipeline cũ

**Alternatives considered**:
- **CLI import trực tiếp từ `src.agents.pipeline`**: Breaking change cho mọi consumer hiện tại
- **Feature flag trong CLI**: Thêm complexity không cần thiết

## Decision 6: Error Handling in Nodes

**Decision**: Mỗi node wrap logic trong try/catch, trả về error state thay vì raise exception.

**Rationale**:
- Theo FR-007: mỗi agent node PHẢI xử lý lỗi nội bộ để tránh crash pipeline
- Node bị lỗi ghi `error` vào state, Supervisor đọc và trả fallback message
- Log chi tiết lỗi cho debugging

**Alternatives considered**:
- **Global exception handler ở graph level**: LangGraph có retry mechanism nhưng không phù hợp cho LLM API errors (vì rate-limit)
- **Let it crash**: Vi phạm FR-007, UX tệ

## Decision 7: Harm Assessment Classification

**Decision**: Harm Assessment Agent phân loại câu hỏi thành 4 category: `SAFE`, `PRESCRIPTION`, `DIAGNOSIS`, `EMERGENCY`.

**Rationale**:
- Theo FR-003: phân loại AN TOÀN, KÊ ĐƠN, CHẨN ĐOÁN, CẤP CỨU
- Mỗi category có câu từ chối chuẩn y tế riêng (FR-006)
- Tái sử dụng prompt logic từ `guardrail.py` hiện tại, nhưng mở rộng output format

**Mapping từ chối**:
- `PRESCRIPTION` → "Xin lỗi, tôi không thể kê đơn thuốc. Vui lòng tham khảo ý kiến bác sĩ."
- `DIAGNOSIS` → "Xin lỗi, tôi không thể chẩn đoán bệnh. Vui lòng đến cơ sở y tế."
- `EMERGENCY` → "⚠️ Tình huống khẩn cấp! Vui lòng gọi 115 hoặc đến phòng cấp cứu ngay."
