# Research: UC-010 Bypass RAG

**Feature**: UC-010 — Trò chuyện thông thường (Bypass RAG)
**Date**: 2026-07-03

---

## Context

The existing pipeline is:
```
START → harm_assessment → supervisor → rag_agent → response_agent → END
                                    ↘ END (if unsafe)
```

The Harm Assessment node already blocks dangerous queries (prescription, diagnosis, emergency). The Supervisor node is currently a lightweight pass-through with no classification logic. UC-010 promotes Supervisor to be the **intent classifier** for safe queries.

---

## Decisions

### D-01: Which node owns intent classification?

- **Decision**: The **Supervisor node** classifies safe messages into `SMALL_TALK` vs `DIABETES` (requires RAG).
- **Rationale**: The spec explicitly states "Supervisor Node nhận diện đây là câu hỏi giao tiếp cơ bản." Harm Assessment already runs before Supervisor and handles the unsafe path — it is already the safety gate. Supervisor's current role is trivially a pass-through, making it the natural place to add intent routing without adding a new node or changing graph topology.
- **Alternatives considered**:
  - **Harm Node classifies all 4 intents**: Violates single-responsibility — guardrail and intent are different concerns; also contradict the spec's updated wording.
  - **New `intent_classifier` node**: Would change graph topology unnecessarily. Spec says Supervisor does this.

---

### D-02: How to represent intent in AgentState

- **Decision**: Add `intent: str` to `AgentState` with values `"SMALL_TALK"` or `"DIABETES"`. Set by `supervisor_node`, read by the graph router and `response_agent`.
- **Rationale**: A simple `str` field is the least invasive change. Alternatively we could extend `SafetyCategory` with `SMALL_TALK`, but that enum belongs to Harm Assessment's concern (safety categories), not routing intent. Mixing them would make the enum semantically inconsistent.
- **Alternatives considered**:
  - `requires_rag: bool` field: Simpler, but loses the semantic label needed for `response_agent` to know it's in a small-talk context.
  - Extend `SafetyCategory` enum: Mixes safety classification with intent classification — two different concerns in one enum.

---

### D-03: How Supervisor classifies intent

- **Decision**: Supervisor calls ChatGroq with a focused 2-label prompt (`SMALL_TALK` / `DIABETES`) on messages that pass harm assessment (`is_safe=True`).
- **Rationale**: Rule-based keyword matching is too brittle for Vietnamese ("cảm ơn bác sĩ vì đã giải thích về đường huyết" contains diabetes keywords but is small talk). LLM classification is already used in `guardrail.py` — the same pattern is consistent with the codebase.
- **Prompt design**:
  - `SMALL_TALK`: greetings, thanks, farewells, casual chat — user is NOT asking for medical information.
  - `DIABETES`: user is asking a question or seeking information about diabetes or related health topics.
- **Alternatives considered**:
  - Keyword list: Fast but brittle; misclassifies edge cases.
  - Reuse guardrail LLM result: Guardrail returns only `is_safe` + `reason`; it does not distinguish `SMALL_TALK` from `DIABETES`.

---

### D-04: Routing change in graph.py

- **Decision**: Rename `_route_after_supervisor` logic to route on the new `intent` field:
  - `is_safe=False` → `END` (unchanged)
  - `intent == "SMALL_TALK"` → `response_agent`
  - `intent == "DIABETES"` → `rag_agent`
- **Rationale**: The conditional edge is already after supervisor; only the routing logic changes, not the graph topology (no new nodes or edges needed beyond adding `"response_agent"` to the conditional edge map).

---

### D-05: response_agent on SMALL_TALK path

- **Decision**: `response_agent_node` checks `state.get("intent") == "SMALL_TALK"`. If true, calls new `generate_small_talk(query)` instead of `generate(query, context)`.
- **Rationale**: `generate()` requires non-empty `rag_context` (the generator's no-chunk fallback returns a "not found" message, which is wrong for small talk). A separate function keeps generator logic clean and untangled.

---

### D-06: generate_small_talk prompt

- **Decision**: Use a simple LLM call with a system prompt establishing the DiaCareFlow persona, no document context injected.
- **Rationale**: Small talk only needs the chatbot's persona to respond naturally. The existing `GENERATIVE_MODEL` (ChatGroq) is used for consistency.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Supervisor LLM call adds latency to ALL safe requests | Supervisor classification prompt is small (2-label, no documents); latency delta is minimal. Could be cached for identical inputs in future. |
| Diabetes question misclassified as SMALL_TALK | Prompt instructs: if user is asking a question or seeking info → DIABETES. Expressions of gratitude/greeting → SMALL_TALK. |
| `intent` field missing in state (default) causes routing failure | Set `intent` default to `"DIABETES"` in supervisor (fail-safe: prefer RAG over missing small-talk response). |
