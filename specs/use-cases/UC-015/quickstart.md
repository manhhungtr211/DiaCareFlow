# Quickstart (UC-015)

## Prerequisites
- Start server: `uvicorn src.api.main:app --reload`

## Testing via CLI (curl)

### AC-1: Happy Path
Trigger a question that involves all three agents: factors, suggestions, and harms.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Người tiền tiểu đường nên ăn gì?"}'
```

**Expected Outcome**:
1. Server logs show the request passing `triage_agent`.
2. `supervisor` classifies intent as `DIABETES`, sets `should_response=False`, and generates tasks.
3. Sub-agents execute **in parallel**.
4. `response_agent` synthesizes a comprehensive response based ONLY on the provided context (no hallucination).

### AC-2: Unsafe Path
Trigger an unsafe/emergency question.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị hạ đường huyết ngất xỉu, cần gọi cấp cứu!"}'
```

**Expected Outcome**:
1. `triage_agent` uses `check_guardrail` which classifies it as an emergency (`is_safe=False`).
2. Graph routes directly to `response_agent`.
3. Returns a refusal/warning message immediately without invoking the LLM for generation.
