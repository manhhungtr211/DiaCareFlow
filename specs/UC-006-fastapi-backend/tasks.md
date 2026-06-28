# Tasks: UC-006 FastAPI Backend REST API

**Input**: Design documents from `/specs/UC-006-fastapi-backend/`


## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (per plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `src/api/` module structure and install dependencies

- [X] T001 Create API module structure with `src/api/__init__.py` and `tests/api/__init__.py`
- [X] T002 [P] Add FastAPI, Uvicorn, and httpx (for TestClient) to project dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Define Pydantic schemas (`ChatRequest`, `SourceItem`, `ChatResponse`, `HealthResponse`) in `src/api/schemas.py` per data-model.md
- [X] T004 [P] Create FastAPI application instance with CORS middleware and global exception handler in `src/api/main.py`
- [X] T005 [P] Create empty route module with router in `src/api/routes.py` and register it in `src/api/main.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Chat Q&A Happy Path (Priority: P1) 🎯 MVP

**Goal**: Client sends `POST /api/chat` with a valid question and receives a JSON response containing the answer, sources, and metadata.

**Independent Test**: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"question": "Tiền tiểu đường là gì?"}'` → HTTP 200 with `text`, `sources`, `is_refused: false`, `metadata.processing_time_ms`.


**Checkpoint**: User Story 1 should be fully functional — `POST /api/chat` returns an answer for valid questions

---

## Phase 4: User Story 2 — Refusal Handling (Priority: P1)

**Goal**: When the pipeline refuses a question (e.g., medical prescription request), the API returns HTTP 200 with `is_refused: true` and a `refuse_reason`.

**Independent Test**: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"question": "Kê đơn Metformin cho tôi"}'` → HTTP 200 with `is_refused: true`, `refuse_reason` present, `sources: []`.



## Phase 5: User Story 3 — Input Validation (Priority: P1)

**Goal**: Invalid requests (missing `question`, empty body, question > 2000 chars) return HTTP 422 with clear validation error messages.

**Independent Test**: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{}'` → HTTP 422 with validation error details.

### Implementation for User Story 3

- [X] T012 [US3] Add `max_length=2000` and `min_length=1` validators to `ChatRequest.question` in `src/api/schemas.py` (done as part of T003)

**Checkpoint**: User Story 3 should be fully functional — invalid inputs are properly rejected

---

## Phase 6: User Story 4 — Health Check (Priority: P1)

**Goal**: `GET /api/health` returns system status including Qdrant connectivity.

**Independent Test**: `curl -X GET http://localhost:8000/api/health` → HTTP 200 with `{"status": "ok", "qdrant": "connected", "version": "1.0.0"}`. If Qdrant is down → `{"status": "degraded", "qdrant": "disconnected", "version": "1.0.0"}`.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [P] [US4] Write tests for `GET /api/health` (healthy → `status: ok`, Qdrant down → `status: degraded`) in `tests/api/test_routes.py`

### Implementation for User Story 4

- [X] T014 [US4] Implement `GET /api/health` endpoint in `src/api/routes.py`: check Qdrant connectivity, return `HealthResponse` with appropriate status

**Checkpoint**: User Story 4 should be fully functional — health check reports system status

---


## Phase 9: User Story 7 — Error Handling (Priority: P1)

**Goal**: Pipeline internal errors (LLM timeout, Qdrant disconnect) return HTTP 500 with a friendly error message, no stack trace leaked.

**Independent Test**: Simulate pipeline exception → API returns HTTP 500 with `{"detail": "Internal server error. Please try again later."}`.

### Tests for User Story 7

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T019 [P] [US7] Write test for pipeline exception → HTTP 500 with generic error (no stack trace) in `tests/api/test_routes.py`

### Implementation for User Story 7

- [X] T020 [US7] Implement global exception handler in `src/api/main.py` to catch unhandled exceptions from pipeline, log internally, and return HTTP 500 with friendly message (done via CatchAllExceptionMiddleware)

**Checkpoint**: User Story 7 should be fully functional — internal errors handled gracefully

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and improvements that affect multiple user stories

- [ ] T021 [P] Run all tests with `pytest tests/api/` and verify all pass
- [ ] T022 Run quickstart.md validation scenarios manually against live server
- [X] T023 [P] Review and finalize docstrings and inline comments in `src/api/main.py`, `src/api/routes.py`, `src/api/schemas.py`

---


---

## Parallel Example: After Phase 2

```text
# These user stories can launch in parallel (different endpoints/concerns):
Developer A: US1 (Chat Q&A) → T006 → T007 → T008
Developer B: US4 (Health Check) → T013 → T014
Developer C: US3 (Validation) → T011 → T012
Developer D: US5 (CORS) + US6 (Swagger) → T015 → T016 → T017 → T018

# After US1 completes:
Developer A: US2 (Refusal) → T009 → T010
Developer A: US7 (Error Handling) → T019 → T020
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: User Story 1 — Chat Q&A (T006–T008)
4. **STOP and VALIDATE**: Test `POST /api/chat` with a real question
5. Deploy/demo if ready

