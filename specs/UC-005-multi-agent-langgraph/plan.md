# Implementation Plan: UC-005 — Multi-Agent Pipeline LangGraph

**Date**: 2026-06-23 | **Spec**: [UC-005.md](../use-cases/UC-005.md)

**Input**: Feature specification from `specs/use-cases/UC-005.md`


**Dependencies mới**:
- `langgraph>=0.4.0` — Framework đồ thị trạng thái cho multi-agent orchestration

## Technical Context


**Constraints**: Tương thích ngược với `python -m src.cli ask`. Guardrail Coverage = 100%. Retrieval Accuracy ≥ 90%.

**Scale/Scope**: 4 agent nodes, 20 test cases


## Project Structure

### Documentation (this feature)

```text
specs/UC-005-multi-agent-langgraph/
├── plan.md              # This file
├── research.md          # Nghiên cứu LangGraph patterns
├── data-model.md        # AgentState và entities
├── quickstart.md        # Hướng dẫn chạy và validate
├── contracts/           # Interface contracts
│   └── cli-ask-v2.md   # CLI ask contract (backward compatible)
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── agents/                          # [NEW] Module Multi-Agent LangGraph
│   ├── __init__.py
│   ├── state.py                     # AgentState (TypedDict) — trạng thái chia sẻ giữa nodes
│   ├── nodes/                       # [NEW] Các agent nodes
│   │   ├── __init__.py
│   │   ├── supervisor.py            # Supervisor Agent — điểm vào, routing logic
│   │   ├── harm_assessment.py       # Harm Assessment Agent — đánh giá an toàn (wrap guardrail.py)
│   │   ├── rag_agent.py             # RAG Agent — truy xuất tài liệu (wrap retriever.py)
│   │   └── response_agent.py        # Response Agent — tổng hợp câu trả lời (wrap generator.py)
│   ├── graph.py                     # [NEW] Xây dựng StateGraph, routing, compile
│   └── pipeline.py                  # [NEW] Entry point: ask() tương thích ngược với pipeline cũ
├── rag/
│   └── qa/                          # [KEEP] Giữ nguyên, tái sử dụng bên trong agents
│       ├── guardrail.py
│       ├── retriever.py
│       ├── generator.py
│       ├── pipeline.py              # [MODIFY] Delegate sang agents.pipeline khi LangGraph enabled
│       └── data_models.py           # [KEEP] Giữ nguyên                 
└── cli.py                           # [MINIMAL CHANGE] Vẫn import từ src.rag.qa.pipeline.ask
```

**Structure Decision**: Tạo module `src/agents/` riêng cho LangGraph orchestration. Giữ nguyên `src/rag/qa/` làm "primitive layer". Module agents wrap các primitives và thêm trạng thái + routing. `src/rag/qa/pipeline.py` delegate sang `src/agents/pipeline.py` để đảm bảo backward compatibility cho CLI.
