# Quickstart Validation: UC-006 FastAPI Backend REST API

This guide provides commands to manually validate the REST API endpoints.

## Prerequisites
- The environment is set up (Python 3.11+, dependencies installed including `fastapi` and `uvicorn`).
- Qdrant is running locally on port 6333.
- LLM API keys are set in the `.env` file.

## 1. Start the Server
Start the FastAPI server using Uvicorn:
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```
Expected output: Uvicorn starts and listens on `http://127.0.0.1:8000`.

## 2. Validation Scenarios

### Scenario 1: Health Check (AC-4)
```bash
curl -X GET http://localhost:8000/api/health
```
**Expected Outcome**: HTTP 200 OK. JSON: `{"status": "ok", "qdrant": "connected", "version": "1.0.0"}`

### Scenario 2: Happy Path Q&A (AC-1)
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "Tiền tiểu đường là gì?"}'
```
**Expected Outcome**: HTTP 200 OK. JSON contains `text` (the answer), `sources` (list of documents), and `is_refused: false`.

### Scenario 3: Refusal Path (AC-2)
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"question": "Kê đơn Metformin cho tôi"}'
```
**Expected Outcome**: HTTP 200 OK. JSON contains `is_refused: true` and `refuse_reason` explaining the medical policy.

### Scenario 4: Validation Error - Empty Body (AC-3)
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{}'
```
**Expected Outcome**: HTTP 422 Unprocessable Entity. JSON contains validation error details about the missing `question` field.

### Scenario 5: Swagger UI (AC-6)
Open a browser and navigate to:
`http://localhost:8000/docs`
**Expected Outcome**: The OpenAPI Swagger UI page loads, displaying the `/api/chat` and `/api/health` endpoints.
