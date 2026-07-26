# Quickstart: Testing the Multi-Agent Flow (UC-012)

## Prerequisites
- Server đang chạy: `uvicorn src.api.main:app --reload`
- Web UI (Tùy chọn): `npm run dev` trong thư mục `frontend/`

## Testing via CLI (curl)

To validate the happy path (AC-1), trigger a question that involves all three agents: factors (causes), suggestions, and harms.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bệnh tiểu đường có những nguyên nhân nào, cách phòng ngừa ra sao và có nguy hiểm không?"}'
```

**Expected Outcome**:
1. Server logs show the request passing `triage_agent`.
2. `supervisor` classifies intent as `DIABETES`, sets `should_response=False`, and generates `factor_task`, `suggestion_task`, and `harm_task`.
3. `factor_agent`, `suggestion_agent`, and `harm_agent` execute **in parallel**, generating sub-queries and returning their respective `StateOutput`.
4. `response_agent` consumes the lists from `factor_results`, `suggestion_results`, and `harm_results` to synthesize a comprehensive response.

## AC-2: Unsafe Path (Emergency/Refusal)

To validate the unsafe path where the user asks an emergency or off-topic question, the sub-agents should be completely bypassed.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị hạ đường huyết ngất xỉu, cần gọi cấp cứu!"}'
```

**Expected Outcome**:
1. Server logs show the request hitting `triage_agent`.
2. `triage_agent` uses `check_guardrail` which classifies it as an emergency (`is_safe=False`).
3. The graph bypasses `supervisor` and the sub-agents, routing directly to `response_agent`.
4. `response_agent` immediately returns the refusal message (e.g., "⚠️ Tình huống khẩn cấp! Vui lòng gọi 115 hoặc đến phòng cấp cứu ngay.") without invoking the LLM.

## Viewing Traces
Check LangSmith or the standard stdout logs to verify that the 3 sub-agents were triggered in parallel (not sequentially) for AC-1, and that they were skipped for AC-2.
