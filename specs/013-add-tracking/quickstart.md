# Quickstart: Validation Guide for Add Tracking

This guide documents how to validate that the tracking feature is capturing LangGraph events correctly and outputting structured JSON logs.

## Prerequisites

1. The project dependencies must be installed (`pip install -r requirements.txt`).
2. The environment variables (such as `GROQ_API_KEY`) must be configured in `.env`.

## Setup

No special setup is required besides a working DiaCareFlow development environment. The tracking callback handler will be integrated directly into the `ask_langgraph` pipeline invocation.

## Test / Run Commands

Run the CLI tool to interact with the LangGraph pipeline:

```bash
python src/cli.py
```

Ask a question in the CLI prompt, for example:
```text
Bạn tôi mới bị chẩn đoán tiểu đường type 2. Tôi nên khuyên họ ăn uống như thế nào?
```

## Expected Outcomes

1. **Pipeline Execution**: The chatbot should respond to your question normally as before.
2. **JSON Logs**: In the console output (or the configured log file, e.g., `logs/tracking.log`), you should see structured JSON logs corresponding to the execution events.
3. **Log Content**: Verify the JSON logs contain:
   - Event types (`chain_start`, `chain_end`, `llm_end`, etc.).
   - Node names (e.g., `triage_agent`, `supervisor`, `factor_agent`).
   - `latency_ms` calculated for the events.
   - `token_usage` for LLM events.
   - Example snippet:
     ```json
     {"event_type": "chain_end", "name": "triage_agent", "latency_ms": 1205.4, "session_id": "...", "start_time": 1700000000.0, "end_time": 1700000001.205}
     ```
