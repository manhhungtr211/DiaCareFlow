"""
FastAPI application entry point for DiaCareFlow.

Creates the FastAPI app instance, configures CORS middleware,
registers routers, and sets up global exception handling.

Run with:
    python -m uvicorn src.api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

# Configure basic logging to display INFO level messages and above
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.tools.rag.embedding_model import load_bge_m3

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — load heavy resources once before accepting requests (UC-014)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.

    Startup:
        - Load BGE-M3 embedding model into memory (with retry logic).
          If loading fails after 3 attempts, the application exits so that
          the process manager can surface the error clearly.

    Shutdown:
        - No teardown required (model lives in process memory).
    """
    logger.info("Application startup: loading BGE-M3 embedding model…")
    try:
        load_bge_m3(max_retries=3)
    except RuntimeError as exc:
        logger.critical(
            "FATAL: BGE-M3 model could not be loaded. Aborting startup. Error: %s", exc
        )
        raise

    yield  # Application is live — serve requests

    logger.info("Application shutdown complete.")


app = FastAPI(
    title="DiaCareFlow API",
    description="REST API for the DiaCareFlow Diabetes Care Support System. "
    "Wraps the Multi-Agent LangGraph pipeline (UC-005) via a POST /api/chat endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware — allow cross-origin requests from ReactJS UI (AC-5 / E3)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handler Middleware — catch unhandled pipeline errors (E1)
# Returns HTTP 500 with a friendly message; no stack trace leaked.
#
# We use a Starlette middleware instead of @app.exception_handler(Exception)
# because the latter does not reliably catch all unhandled exceptions
# in recent FastAPI/Starlette versions.
# ---------------------------------------------------------------------------
class CatchAllExceptionMiddleware(BaseHTTPMiddleware):
    """Middleware that catches all unhandled exceptions and returns HTTP 500."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled exception on %s %s: %s",
                request.method,
                request.url.path,
                exc,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Please try again later."},
            )


app.add_middleware(CatchAllExceptionMiddleware)


# ---------------------------------------------------------------------------
# Register routers — import after app creation to avoid circular imports
# ---------------------------------------------------------------------------
from src.api.routes import router  # noqa: E402

app.include_router(router)
