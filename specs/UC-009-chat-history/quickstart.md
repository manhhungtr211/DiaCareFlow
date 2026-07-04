# Quickstart: UC-009 Chat History Validation

## Prerequisites

1. Backend running: `uvicorn src.api.main:app --reload`
2. Frontend running: `npm run dev` (in `frontend/`)
3. Qdrant running with indexed documents
4. `.env` configured with `GROQ_API_KEY`, `MODEL`, `QDRANT_URL`, etc.
5. Optional: `CHAT_HISTORY_MAX_TOKENS=4000` in `.env`

---

## Validation Scenario 1: Coreference Resolution (AC-1)

**Goal**: Verify that the bot resolves pronouns using chat history.

### Steps

1. Open the chat UI in a browser
2. Send: `"Tiểu đường là gì?"`
3. Wait for response
4. Send: `"Vậy bệnh đó có mấy loại?"`
5. Verify the response discusses types of diabetes (Type 1, Type 2, gestational)

### Expected Outcome
- The bot understands "bệnh đó" refers to "tiểu đường" from the previous exchange
- The response is contextually accurate, not a generic "I don't know what you're referring to"

### API-level verification (curl)

```bash
# First message — establish context
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tiểu đường là gì?", "session_id": "test-session-001"}'

# Follow-up — uses pronoun
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Vậy bệnh đó có mấy loại?", "session_id": "test-session-001"}'
```

The second response should reference diabetes types, proving the LLM used chat history.

---

## Validation Scenario 2: Token Trimming (AC-2)

**Goal**: Verify that long conversations are trimmed without crashing.

### Steps

1. Using the same `session_id`, send 20+ messages about various diabetes topics
2. Verify responses remain coherent for recent context
3. Verify no HTTP 500 errors or LLM token limit errors in server logs

### Expected Outcome
- System continues to respond normally
- Server logs show `trim_messages` activity (if DEBUG logging enabled)
- No `context_length_exceeded` errors

---

## Validation Scenario 3: Session Isolation (AC-3)

**Goal**: Verify sessions are isolated and reset on page refresh.

### Steps

1. Open chat, send "Tiểu đường là gì?" and get a response
2. Refresh the page (F5)
3. Send "Bệnh đó có mấy loại?" as the first message

### Expected Outcome
- After refresh, the bot does NOT know what "đó" refers to (no prior context)
- Response indicates it doesn't have enough context, or treats it as a new standalone question

### API-level verification

```bash
# Session A
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tiểu đường là gì?", "session_id": "session-A"}'

# Session B (different session_id — simulates page refresh)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Bệnh đó có mấy loại?", "session_id": "session-B"}'
```

Session B should NOT reference diabetes unless the question is clear enough on its own.

---

## Validation Scenario 4: Backward Compatibility

**Goal**: Verify the API works without `session_id` (existing clients).

### Steps

```bash
# No session_id — should still work (auto-generated UUID, no history)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Tiểu đường là gì?"}'
```

### Expected Outcome
- Returns a valid response
- No errors — `session_id` defaults to a random UUID
