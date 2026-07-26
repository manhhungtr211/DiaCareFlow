# Agent State Contract (UC-012)

This document defines the contract for how data flows between the sub-agents and the Response Agent.

## Sub-Agent Output

Each sub-agent (`factor_agent`, `suggestion_agent`, `harm_agent`) **MUST** return a dictionary containing their respective reducer list and a `nodes_visited` update. 

The elements in the reducer list must conform to the `StateOutput` data model.

### Example Factor Agent Output
```python
{
    "factor_results": [{
        "summary": "Tóm tắt nguyên nhân liên quan đến câu hỏi...",
        "sources": [{"url": "...", "content": "..."}]
    }],
    "nodes_visited": ["factor_agent"]
}
```

### Example Suggestion Agent Output
```python
{
    "suggestion_results": [{
        "summary": "Tóm tắt lời khuyên và giải pháp liên quan đến câu hỏi...",
        "sources": [{"url": "...", "content": "..."}]
    }],
    "nodes_visited": ["suggestion_agent"]
}
```

## Response Agent Input

The `response_agent` node will read directly from the `AgentState`. It expects the reducers to contain lists of `StateOutput`. 

```python
factor_results = state.get("factor_results", [])
suggestion_results = state.get("suggestion_results", [])
harm_results = state.get("harm_results", [])

# Tiêu thụ dữ liệu
factor_summary = factor_results[0].get("summary", "") if factor_results else ""
suggestion_summary = suggestion_results[0].get("summary", "") if suggestion_results else ""
harm_summary = harm_results[0].get("summary", "") if harm_results else ""
```
