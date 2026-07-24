# Implementation Plan: UC-015

**Branch**: `N/A` | **Date**: 24/07/2026 | **Spec**: [UC-015-update-archi.md](file:///h:/project/DiaCareFlow/specs/use-cases/UC-015/spec.md)

**Input**: Feature specification from `/specs/use-cases/UC-015/spec.md`

## Summary

The UC-015 specification describes the improved Multi-Agent workflow where the `Supervisor` routes queries to 3 parallel sub-agents (`Factor`, `Suggestion`, `Harm`), whose outputs are collected via a fan-in state model (`operator.add` in LangGraph) and ultimately synthesized by the `Response` agent.

This architecture was fundamentally implemented during the `UC-012` cycle. The goal of this phase is to ensure full compliance with the newly formalized UC-015 specification and rectify any minor documentation/typo inconsistencies in the state and node outputs.

## Technical Context

**Language/Version**: Python 3.10

**Primary Dependencies**: LangGraph, LangChain, FastAPI

**Testing**: pytest

**Target Platform**: Backend Service

**Project Type**: Web API

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Test-First**: Full unit and integration testing have already been implemented for this architecture flow.
- **Simplicity**: Fan-in reducers naturally manage state aggregation without complex manual state threading.

## Open Questions

> [!NOTE]
> The specification mentions "truyền vào ou node", which appears to be a typo for "truyền vào StateOutput của mỗi node". I will assume this is a typo and proceed.
> The existing codebase already fully satisfies AC-1 and AC-2 as per the UC-012 refactor. No new architectural code changes are strictly necessary.

## Proposed Changes

Since the architecture is already in place, there are no structural code changes required. The plan consists of:
1. Generating the required design artifacts (`research.md`, `data-model.md`, `quickstart.md`) — **Done**.
2. Verifying that the current agent prompts strictly adhere to the "không tự sáng tạo ra thông tin" (no hallucination) constraint.
3. Minor cleanup of docstrings in agent nodes to accurately reflect the v3 schema (e.g., removing legacy `harm_sub_results` references from docstrings).

### Documentation (this feature)

```text
specs/use-cases/UC-015/
├── plan.md              # This file
├── research.md          # Completed
├── data-model.md        # Completed
├── quickstart.md        # Completed
```

### Source Code

#### [MODIFY] [harm_agent.py](file:///h:/project/DiaCareFlow/src/agents/nodes/harm_agent.py)
Update docstrings to reference `harm_results` instead of `harm_sub_results` and `StateOutput` to align perfectly with UC-015 terminology.

## Verification Plan

### Automated Tests
Run existing LangGraph integration tests to ensure the parallel sub-agent routing works flawlessly:
- `pytest tests/integration/test_pipeline_multi_agent.py`
- `pytest tests/unit/agents/`

### Manual Verification
Run the AC-1 and AC-2 smoke tests via curl to ensure the server processes the state transitions as specified in `quickstart.md`.
