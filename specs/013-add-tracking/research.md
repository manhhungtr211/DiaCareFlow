# Research: Add Tracking

## Needs Clarification
- How to implement a custom callback handler in LangGraph to track nodes, tools and calculate latency?
- How to extract token usage (resource usage) from the LLM calls within LangGraph?
- Where to output the structured JSON logs in the current architecture?

## Findings & Decisions

### 1. Custom Callback Handler for LangGraph
**Decision**: Implement a subclass of `langchain_core.callbacks.BaseCallbackHandler`.
**Rationale**: LangGraph is built on LangChain. Node executions, tool calls, and LLM calls emit standard LangChain callback events. By implementing `on_chain_start`/`on_chain_end`, we can track LangGraph node execution time. `on_tool_start`/`on_tool_end` tracks tools, and `on_llm_start`/`on_llm_end` tracks LLM executions.
**Alternatives considered**: Using LangSmith (rejected because out of scope for now, as we want to log to a local structured JSON format), or wrapping nodes manually (rejected because it's intrusive and hard to maintain).

### 2. Extracting Token Usage
**Decision**: Extract token usage from the `LLMResult` object passed to the `on_llm_end` callback.
**Rationale**: When using `ChatGroq` or other LangChain-compatible LLMs, the `on_llm_end(response: LLMResult, **kwargs)` callback receives the generation output. The `response.llm_output` dictionary usually contains a `token_usage` field with `prompt_tokens`, `completion_tokens`, and `total_tokens`.
**Alternatives considered**: Polling an external API (rejected because the info is already returned in the LLM response).

### 3. Output Destination
**Decision**: Output to standard output using the Python `logging` module configured with a JSON formatter, or simply append JSON strings 

**Rationale**: A JSON lines (`.jsonl`) file or JSON-formatted `stdout` satisfies the requirement for structured JSON logs without needing an external log aggregation system yet. We will configure a dedicated logger for the tracking handler to output JSON.
**Alternatives considered**: Direct database insertion (rejected due to out of scope assumptions).
