# API Contract: UC-009 Chat History

## Modified Endpoint: POST /api/chat

### Request

```json
{
  "question": "Vậy bệnh đó có mấy loại?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field       | Type   | Required | Description                                              |
|-------------|--------|----------|----------------------------------------------------------|
| question    | string | Yes      | The user's question. 1–2000 chars.                       |
| session_id  | string | No       | UUID v4. Omit for backward compat (auto-generated).      |

### Response

**Unchanged** — still returns raw string (`response_model=str`).

```
"Bệnh tiểu đường có 3 loại chính: Type 1, Type 2 và tiểu đường thai kỳ..."
```

### Behavior Changes

1. **With `session_id`**: Backend uses LangGraph MemorySaver to persist conversation state across requests sharing the same `session_id`. LLM nodes receive trimmed chat history for contextual understanding.

2. **Without `session_id`**: A random UUID is generated per request → no history (backward compatible with existing behavior).

3. **Session lifecycle**: History is in-memory only. Server restart clears all sessions.

---

## Frontend Contract

### Session ID Management

```typescript
// On ChatPage mount: generate new session ID
const sessionId = crypto.randomUUID();

// On every message send: include session_id
POST /api/chat { question: "...", session_id: sessionId }
```

### Session Reset Triggers
- Page refresh → new `useChat()` instance → new UUID
- New tab → new component mount → new UUID
- Explicit "New Chat" button (if added) → regenerate UUID
