# Research: UC-009 Chat History

## R1: LangGraph MessagesState — Built-in Chat History

**Decision**: Use LangGraph's built-in `MessagesState` message accumulation — the `messages` field in `AgentState` already supports this.

**Rationale**: `AgentState` already extends `MessagesState`, which provides automatic message accumulation via `Annotated[list[BaseMessage], add_messages]`. The `messages` field is designed for exactly this use case. We don't need a separate data structure.

**Alternatives considered**:
- Custom list-based history: Rejected — reinvents what MessagesState already provides
- External storage (Redis, DB): Rejected — overkill for session-scoped in-memory history; the spec explicitly states no persistence across sessions (AC-3)

---

## R2: LangChain `trim_messages` for Token Management

**Decision**: Use `langchain_core.messages.trim_messages()` to enforce a token window on the message history before passing to LLM nodes.

**Rationale**: The spec requires token-limited history (US3). `trim_messages` is LangChain's official utility for this — it trims from the beginning of the conversation while preserving the system message and recent turns. It integrates naturally with `ChatGroq` token counting.

**Alternatives considered**:
- Manual slicing (last N messages): Rejected — doesn't account for variable message lengths; can still exceed token limits
- tiktoken manual counting: Rejected — `trim_messages` handles this internally with the model's tokenizer
- LangGraph `MessageGraph` with `messages_modifier`: Considered but overly complex — `trim_messages` as a simple function call within nodes is more explicit and testable

---

## R3: Session Scoping — Frontend-managed Session ID

**Decision**: Generate a `session_id` (UUID) on the frontend when the chat page mounts. Pass it with every `/api/chat` request. Backend uses `session_id` to key a server-side in-memory history store.

**Rationale**: The spec requires history to reset on page refresh (AC-3). A frontend-generated UUID that resets on component mount satisfies this naturally. The backend needs the session ID to associate messages across multiple HTTP requests (the current API is stateless — each POST to `/api/chat` is independent).

**Alternatives considered**:
- Frontend-only history (send full history array in each request): Rejected — increases payload size linearly; exposes full conversation to network inspection; doesn't scale
- LangGraph checkpointer (MemorySaver): Considered — LangGraph supports thread-based persistence via checkpointers. However, this requires compiling the graph with `checkpointer=MemorySaver()` and passing `config={"configurable": {"thread_id": session_id}}` at invocation. This is the most idiomatic LangGraph approach and adds minimal complexity.
  - **Updated decision**: Use `MemorySaver` checkpointer. This is the LangGraph-native way to persist conversation state per thread.

---

## R4: Where to Inject History — All LLM-calling Nodes

**Decision**: Inject trimmed chat history into the prompt of all LLM-calling nodes: `supervisor_node`, `harm_assessment_node`, and the RAG `generator.py`.

**Rationale**: 
- **Supervisor**: Needs history to correctly classify follow-up intents (e.g., "còn loại nào khác?" after a diabetes question should still be classified as DIABETES, not SMALL_TALK)
- **Response Agent / Generator**: Needs history so the LLM can resolve coreference ("bệnh ĐÓ" → diabetes) and provide contextual answers
- **Harm Assessment**: Benefits from history context to avoid false positives on follow-up clarifications

**Alternatives considered**:
- Only inject in generator: Rejected — supervisor would misclassify follow-up questions without context
- Inject everywhere uniformly: The chosen approach, with `trim_messages` ensuring each node gets appropriately sized history

---

## R5: API Contract Change — Adding session_id and chat_history

**Decision**: Add `session_id` (string, optional) to `ChatRequest`. The backend manages history server-side using this ID.

**Rationale**: Minimal API change. The `session_id` is the only new field needed. History is managed server-side, so the frontend doesn't need to send/receive message arrays.

**Alternatives considered**:
- Send full `chat_history` array in request body: Rejected per R3 reasoning
- Cookie-based session: Rejected — more complex, CORS issues, doesn't align with REST API patterns

---

## R6: LangGraph MemorySaver vs Custom Dict Store

**Decision**: Use LangGraph's `MemorySaver` checkpointer for the simplest, most idiomatic approach.

**Rationale**: `MemorySaver` is LangGraph's built-in in-memory checkpointer. By compiling the graph with `checkpointer=MemorySaver()` and invoking with `config={"configurable": {"thread_id": session_id}}`, LangGraph automatically persists the `messages` field across invocations for the same thread. This removes the need for any manual history management in the pipeline layer.

**Alternatives considered**:
- Custom `dict[str, list[BaseMessage]]` in `pipeline.py`: Works but requires manual management of history insertion, retrieval, and cleanup — LangGraph already solves this
- `SqliteSaver` for persistence: Overkill — spec says no cross-session persistence (AC-3)

**Key implementation detail**: When using `MemorySaver`, the `messages` field in `AgentState` automatically accumulates across invocations. The `trim_messages` utility should still be used within nodes to avoid sending excessively long histories to the LLM.
