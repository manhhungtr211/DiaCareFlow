# Quickstart / Validation Guide: UC-014

## Setup Prerequisites
1. Ensure you have the BGE-M3 model files downloaded and placed at `src/agents/embedding_model/bge-m3`.

## Validation Scenarios

### Scenario 1: Model loads successfully on startup
1. Run the FastAPI server: `uvicorn src.api.main:app --reload`
2. **Expected Outcome**: The terminal should log an info message indicating that the BGE-M3 model is being loaded, and shortly after, an info message that it was loaded successfully. The application should finish startup and accept requests.

### Scenario 2: Model file is missing (Retry and Failure)
1. Rename the folder `src/agents/embedding_model/bge-m3` to something else (e.g. `bge-m3-hidden`).
2. Run the FastAPI server: `uvicorn src.api.main:app --reload`
3. **Expected Outcome**: The terminal should log that it failed to load the model and is retrying. After 3 failed attempts, the application should output a clear error message instructing the user to download the model, and then the application startup should fail/exit.

### Scenario 3: Memory persistence during inference
1. Make an API request to the chatbot endpoint that triggers RAG.
2. **Expected Outcome**: The request should process significantly faster (because the `BGEM3FlagModel` is not re-instantiated during the request), and the answer should remain accurate.
