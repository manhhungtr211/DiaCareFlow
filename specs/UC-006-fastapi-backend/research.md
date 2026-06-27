# Research: UC-006 FastAPI Backend REST API

## Decisions

### Decision 1: Framework Choice
- **Decision**: Use `FastAPI` + `Uvicorn`.
- **Rationale**: FastAPI provides built-in Pydantic validation, automatic Swagger UI (`/docs`), and asynchronous support. It perfectly aligns with the requirements of UC-006 (Validation, Swagger docs).
- **Alternatives considered**: Flask (lacks native async and built-in type validation), Django (too heavy for a simple REST wrapper).

### Decision 2: Schema Definition
- **Decision**: Define Pydantic models `ChatRequest`, `ChatResponse`, `SourceItem` in `src/api/schemas.py`.
- **Rationale**: Separates API contracts from core data models, allowing the API layer to evolve independently of the pipeline's `Answer` dataclass.
- **Alternatives considered**: Reusing `src.rag.qa.data_models.Answer` directly. Rejected because API responses often need specific formatting (like wrapping in JSON envelopes) that shouldn't pollute core domain models.


### Decision 3: Error Handling
- **Decision**: Use FastAPI Exception Handlers for 500 errors to catch unhandled pipeline exceptions, returning a generic friendly message per Exception E1.
- **Rationale**: Prevents stack traces from leaking to the client while still logging the error internally.
