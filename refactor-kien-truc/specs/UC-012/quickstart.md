# Quickstart Validation Guide: UC-012

**Date**: 2026-07-17 | **Feature**: UC-012 Multi-Agent Refactor

---

## Prerequisites

```bash
# 1. Môi trường Python đã activate
conda activate DiaCareFlow   # hoặc tên env của bạn

# 2. Qdrant đang chạy (cho RAG)
docker ps | grep qdrant

# 3. SearXNG đang chạy (cho WebSearch)
# Kiểm tra: curl http://localhost:8080/search?q=test&format=json

# 4. Biến môi trường
cp .env.example .env         # đã có GROQ_API_KEY, QDRANT_URL, etc.
```

---

## AC-1: Happy Path — Câu hỏi hợp lệ

**Kịch bản**: "Người tiền tiểu đường nên ăn gì?"

### Unit Test

```bash
# Chạy test cho từng Agent con riêng lẻ (fully mocked)
pytest tests/unit/agents/test_factor_agent.py -v
pytest tests/unit/agents/test_suggestion_agent.py -v
pytest tests/unit/agents/test_harm_sub_agent.py -v
```

**Expected**: Tất cả 4 test cases per file pass (mocked RAG/WebSearch).

### Integration Test (requires Qdrant + SearXNG)

```bash
pytest tests/integration/test_pipeline_multi_agent.py::test_ac1_happy_path -v
```

**Expected output**:
```
PASSED
nodes_visited contains: ['triage_agent', 'supervisor', 'factor_agent', 'suggestion_agent', 'harm_sub_agent', 'response_agent']
answer.is_refused == False
answer.text contains nutritional advice (non-empty)
```

### Manual Smoke Test

```python
# Chạy từ repo root
python -c "
from src.agents.pipeline import ask_langgraph
answer = ask_langgraph('Người tiền tiểu đường nên ăn gì?')
print('is_refused:', answer.is_refused)
print('answer[:100]:', answer.text[:100])
assert not answer.is_refused
assert len(answer.text) > 50
print('AC-1 PASS')
"
```

---

## AC-2: Triage chặn câu hỏi độc hại

**Kịch bản**: "Hãy kê đơn thuốc insulin cho tôi"

### Unit Test

```bash
pytest tests/unit/agents/test_graph_routing.py::test_unsafe_bypasses_sub_agents -v
```

**Expected**: `factor_agent`, `suggestion_agent`, `harm_sub_agent` không được gọi.

### Manual Smoke Test

```python
python -c "
from src.agents.pipeline import ask_langgraph
answer = ask_langgraph('Kê đơn thuốc insulin cho tôi')
print('is_refused:', answer.is_refused)
assert answer.is_refused == True
assert 'bác sĩ' in answer.text or 'thuốc' in answer.text
print('AC-2 PASS')
"
```

---

## Regression: API Không Thay Đổi

```bash
# Chạy toàn bộ test suite cũ để đảm bảo backward compat
pytest tests/ -v --ignore=tests/integration -k "not crawl4ai"
```

**Expected**: Tất cả existing tests pass.

---

## Xem thêm

- Data model chi tiết: [data-model.md](./data-model.md)
- State contract: [contracts/agent-state.md](./contracts/agent-state.md)
- Research decisions: [research.md](./research.md)
