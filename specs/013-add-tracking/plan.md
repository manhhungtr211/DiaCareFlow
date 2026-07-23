# Implementation Plan: Add Tracking

**Branch**: `013-add-tracking` | **Date**: 2026-07-21 | **Spec**: [specs/013-add-tracking/spec.md](file:///h:/project/DiaCareFlow/specs/013-add-tracking/spec.md)

**Input**: Feature specification from `/specs/013-add-tracking/spec.md`

## Summary

This feature implements a custom callback handler for LangGraph to track 100% of pipeline events (node start/end, LLM calls). It generates structured JSON logs containing latency metrics, event types, and resource usage (e.g., token usage) for LLM interactions. The tracking will be integrated directly into the `ask_langgraph` pipeline entry point.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: langgraph, langchain, langchain-core

**Storage**: Local JSON lines file (`logs/tracking.jsonl`) or JSON-formatted `stdout`

**Testing**: pytest

**Target Platform**: Linux server / Backend API

**Project Type**: Python library/web-service

**Performance Goals**: < 100ms logging overhead

**Constraints**: JSON log format, must not interfere with pipeline execution

**Scale/Scope**: 100% of graph execution events tracked, per-session granularity

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Observability**: Structured logging is required. We are implementing JSON structured logs. (Passed)
- **Library-First / Test-First**: Will ensure tracking handler has isolated unit tests before integrating. (Passed)

## Project Structure

### Documentation (this feature)

```text
specs/013-add-tracking/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── agents/
│   ├── pipeline.py      # Entry point to be modified to attach callback
│   └── callbacks.py     # NEW file for custom LangGraph callback handler
tests/
└── unit/
    └── test_callbacks.py # NEW file for testing the callback handler
```

**Structure Decision**: Added a new `callbacks.py` file within the `agents` package to keep the tracking handler logically grouped with the graph execution.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*(No violations found)*
