# Data Model: UC-005 — Multi-Agent Pipeline LangGraph

## Entity: AgentState (TypedDict)

Trạng thái dùng chung giữa các nodes trong đồ thị LangGraph. Mỗi node đọc/ghi vào state dict này.

```python
from typing import TypedDict, Optional
from enum import Enum

class SafetyCategory(str, Enum):
    SAFE = "SAFE"
    PRESCRIPTION = "PRESCRIPTION"
    DIAGNOSIS = "DIAGNOSIS"
    EMERGENCY = "EMERGENCY"

class AgentState(TypedDict, total=False):
    # Input
    user_input: str                           # Câu hỏi gốc từ người dùng
    messages: Annotated[List[bytes], lambda x, y: x + y]  # Lịch sử hội thoại
    # Harm Assessment output
    is_safe: bool                           # Kết quả đánh giá an toàn
    harm_task: SafetyCategory         # Phân loại: SAFE/PRESCRIPTION/DIAGNOSIS/EMERGENCY
    rag_context: list                       # Danh sách ChunkResult từ retriever
    suggestion_context: dict                       # Câu trả lời cuối cùng
    messageId: str                           # ID tin nhắn
```

---

## Entity: SafetyCategory (Enum)

Phân loại mức độ an toàn của câu hỏi, được sử dụng bởi Harm Assessment Agent.

| Value | Mô tả | Hành động |
|-------|--------|-----------|
| `SAFE` | Câu hỏi an toàn, liên quan tiểu đường | Tiếp tục pipeline → RAG → Response |
| `PRESCRIPTION` | Yêu cầu kê đơn thuốc | Ngắt pipeline, trả từ chối |
| `DIAGNOSIS` | Yêu cầu chẩn đoán bệnh | Ngắt pipeline, trả từ chối |
| `EMERGENCY` | Tình huống cấp cứu | Ngắt pipeline, trả cảnh báo 115 |

---

## Entities tái sử dụng (từ Tuần 1)

Các entity sau đã tồn tại trong `src/rag/qa/data_models.py` và được tái sử dụng:

- **Query**: `text: str`, `timestamp: datetime` — Đầu vào câu hỏi (validate rỗng, >500 từ)
- **ChunkResult**: `content: str`, `source: str`, `score: float` — Một chunk kết quả retrieval
- **RetrievedContext**: `chunks: list[ChunkResult]`, `query_vector: list[float]` — Kết quả retrieval
- **Answer**: `text: str`, `sources: list[ChunkResult]`, `is_refused: bool`, `refuse_reason: str|None` — Câu trả lời cuối cùng
- **GuardrailResult**: `is_safe: bool`, `reason: str|None` — Kết quả guardrail

### Mapping AgentState ↔ Existing Models

| AgentState field | Maps to existing model |
|-----------------|----------------------|
| `question` | `Query.text` |
| `is_safe` | `GuardrailResult.is_safe` |
| `refusal_message` | `GuardrailResult.reason` / `Answer.refuse_reason` |
| `rag_context` | `RetrievedContext.chunks` (serialized) |
| `final_answer` | `Answer.text` |
| `sources` | `Answer.sources` |

---

## Graph Topology

```
                    ┌──────────────┐
                    │  START       │
                    └──────┬───────┘
                           │
                    ┌──────▼───────────┐
                    │ Harm Assessment  │
                    └──────┬───────────┘
                           │
                    ┌──────▼───────────┐
                    │  Supervisor      │
                    └──────┬───────────┘
                           │
                    ┌──────▼───────────┐
                    │ is_safe?         │
                    └──┬──────┬────────┘
                  Yes  │      │  No
                       │      │
                ┌──────▼──┐   │
                │RAG Agent│   │
                └──────┬──┘   │
                       │      │
             ┌─────────▼──┐   │
             │  Response  │   │
             │  Agent     │   │
             └─────────┬──┘   │
                       │      │
                    ┌──▼──────▼──┐
                    │    END     │
                    └────────────┘
```
