# Data Model: UC-006 FastAPI Backend REST API

## API Schemas

The following Pydantic schemas will be defined in `src/api/schemas.py`.

### 1. `ChatRequest`
**Purpose**: Validates incoming POST requests to `/api/chat`.
- `question` (str): The user's question. Must not be empty and must be <= 2000 characters.

### 2. `SourceItem`
**Purpose**: Represents a single document source used for generating the answer.
- `source` (str): The name/path of the source document.
- `score` (float): The retrieval relevance score.

### 3. `ChatResponse`
**Purpose**: Standardized JSON response returned to the client.
- `text` (str): The generated answer or a fallback string (e.g., empty if refused).
- `is_refused` (bool): True if the question was blocked by guardrails or refused by the LLM.
- `refuse_reason` (str | None): The reason for refusal, if `is_refused` is true.
- `sources` (list[SourceItem]): List of sources used. Empty if refused.
- `metadata` (dict): Additional information, e.g., `{"processing_time_ms": 1200}`.

### 4. `HealthResponse`
**Purpose**: Response for the `/api/health` endpoint.
- `status` (str): `"ok"` or `"degraded"`.
- `qdrant` (str): `"connected"` or `"disconnected"`.
- `version` (str): API version (e.g., `"1.0.0"`).
