# Data Model: UC-014

No new database entities or complex data structures are introduced in this feature.
The primary state change is in the FastAPI application state.

### `app.state`
- `embedding_model`: An instance of `BGEM3FlagModel` from the `FlagEmbedding` library.

### `AgentState` (LangGraph)
- Needs a mechanism to receive the `embedding_model` instance so it can pass it down to `retriever.py`, or we can pass it via `config` (RunnableConfig).
