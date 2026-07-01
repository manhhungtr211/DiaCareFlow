# Tasks: UC-001 — Hỏi đáp Y khoa về Tiểu đường

**Input**: Design documents from `specs/UC-001-hoi-dap/`

## Phase 1: Setup

- [x] T001 Create module directory structure `src/rag/qa/` and `tests/unit/`, `tests/integration/`
- [x] T002 Add `__init__.py` to `src/rag/qa/`
- [x] T003 Update `src/config.py` for Gemini model config

## Phase 2: Foundational 

- [x] T004 Implement `src/rag/qa/data_models.py` with `Query`, `ChunkResult`, `RetrievedContext`, `Answer`, `GuardrailResult`
- [x] T005 [P] Create `tests/unit/test_guardrail.py` and `tests/unit/test_retriever.py` and `tests/unit/test_generator.py` setup

## Phase 3: User Story 1 - Hỏi đáp an toàn (MVP)

- [x] T006 [P] [US1] Implement Guardrail in `src/rag/qa/guardrail.py`
- [x] T007 [P] [US1] Implement Retriever in `src/rag/qa/retriever.py` using Qdrant (top_k=3)
- [x] T008 [P] [US1] Implement Generator in `src/rag/qa/generator.py` using Gemini API
- [x] T009 [US1] Implement Orchestrator in `src/rag/qa/pipeline.py` connecting guardrail -> retrieve -> generate
- [x] T010 [US1] Implement CLI command `ask` in `src/cli.py`
- [x] T011 [US1] Refactor Retriever for 2-stage retrieval (Qdrant top 20 + Jina Reranker top 3)

## Phase 4: Polish & Validation

- [x] T011 Run unit tests `pytest tests/unit/test_guardrail.py tests/unit/test_retriever.py tests/unit/test_generator.py -v`
- [x] T012 Run integration test `pytest tests/integration/test_qa_pipeline.py -v` (requires Qdrant)
- [x] T013 Update `quickstart.md` if necessary
