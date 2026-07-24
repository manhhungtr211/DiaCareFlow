# Phase 0: Research

**Decision**: The multi-agent implementation will use LangGraph's Send API to fan-out queries to `factor_agent`, `suggestion_agent`, and `harm_agent` concurrently. 
**Rationale**: This achieves parallel execution which reduces latency.

**Decision**: `StateOutput` will be defined as a Pydantic Model (`TypedDict` or `BaseModel`) for the output of each sub-agent node, rather than a single aggregated dictionary injected into `AgentState`.
**Rationale**: This aligns with the new requirement to remove `aggregate_node` and have `Response Agent` directly consume a list of `StateOutput` instances from the `AgentState` reducers (`factor_results`, `suggestion_results`, `harm_results`).

**Alternatives considered**: Using a single global `state_output` field via an `aggregate_node`. Rejected because it introduces an unnecessary bottleneck node and goes against the updated architectural spec which requires `StateOutput` to be defined in each node's model and passed through standard LangGraph reducers to the `Response Agent`.
