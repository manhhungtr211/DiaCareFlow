# Implementation Plan: UC-009 Chat History (Context)

**Branch**: `009-chat-history` | **Date**: 2026-07-04 | **Spec**: [spec.md](file:///h:/project/DiaCareFlow/specs/UC-009-chat-history/spec.md)

**Input**: Feature specification from `specs/UC-009-chat-history/spec.md`

## Summary

Enable multi-turn conversational context by leveraging LangGraph's `MemorySaver` checkpointer and LangChain's `trim_messages` utility. The system will maintain per-session chat history in memory, allowing the LLM to resolve coreferences (e.g., "bệnh ĐÓ") and provide contextually aware responses across consecutive messages within the same browser session.

## Technical Context

**Language/Version**: Python 3.11, TypeScript (React + Vite)

**Primary Dependencies**: LangGraph (StateGraph, MemorySaver), LangChain Core (`trim_messages`), FastAPI, ChatGroq

**Storage**: In-memory via LangGraph `MemorySaver` (no database)

**Testing**: Manual validation via curl and browser (see [quickstart.md](file:///h:/project/DiaCareFlow/specs/UC-009-chat-history/quickstart.md))

**Target Platform**: Linux/Windows server (FastAPI backend), Web browser (React frontend)

**Project Type**: Web application (backend + frontend)

**Constraints**: Token limit for chat history configurable via `CHAT_HISTORY_MAX_TOKENS` (default 4000)

## Constitution Check

*GATE: Constitution is a template (not filled in) — no gates to enforce. Proceeding.*

## Project Structure

### Documentation (this feature)

```text
specs/UC-009-chat-history/
├── plan.md              # This file
├── research.md          # Phase 0 output — architecture decisions
├── data-model.md        # Phase 1 output — entities and data flows
├── quickstart.md        # Phase 1 output — validation guide
├── contracts/
│   └── api-contract.md  # Phase 1 output — API changes
└── tasks.md             # Phase 2 output (NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── schemas.py       # [MODIFY] Add session_id to ChatRequest
│   │   └── routes.py        # [MODIFY] Extract session_id, pass to pipeline
│   ├── agents/
│   │   ├── state.py         # [MODIFY] Add chat_history field to AgentState
│   │   ├── graph.py         # [MODIFY] Compile with MemorySaver checkpointer
│   │   ├── pipeline.py      # [MODIFY] Accept session_id, invoke with thread config
│   │   └── nodes/
│   │       ├── supervisor.py      # [MODIFY] Include chat_history in LLM prompt
│   │       ├── harm_assessment.py # [MODIFY] Include chat_history in LLM prompt
│   │       └── response_agent.py  # [MODIFY] Pass chat_history to generator
│   ├── rag/qa/
│   │   └── generator.py     # [MODIFY] Include chat_history in generation prompt
│   └── config.py            # [MODIFY] Add CHAT_HISTORY_MAX_TOKENS

frontend/
├── src/
│   ├── hooks/
│   │   └── useChat.ts       # [MODIFY] Generate session_id, pass with requests
│   └── services/
│       └── chatService.ts   # [MODIFY] Include session_id in POST body
```

**Structure Decision**: Follows existing web application structure (backend `src/` + `frontend/src/`). No new directories needed — modifications to existing files only.

## Complexity Tracking

> No constitution violations — no complexity justifications needed.
