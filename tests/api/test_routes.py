"""
API endpoint tests for DiaCareFlow REST API.

Uses FastAPI TestClient to test /api/chat and /api/health endpoints
with mocked pipeline and Qdrant dependencies.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.rag.qa.data_models import Answer, ChunkResult

client = TestClient(app)


# ---------------------------------------------------------------------------
# /api/health tests (T013 — US4)
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for GET /api/health."""

    @patch("src.api.routes._check_qdrant", return_value="connected")
    def test_health_ok(self, mock_qdrant):
        """Health check returns status=ok when Qdrant is connected."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["qdrant"] == "connected"
        assert data["version"] == "1.0.0"

    @patch("src.api.routes._check_qdrant", return_value="disconnected")
    def test_health_degraded(self, mock_qdrant):
        """Health check returns status=degraded when Qdrant is down."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["qdrant"] == "disconnected"
        assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# /api/chat — happy path tests (US1)
# ---------------------------------------------------------------------------


class TestChatHappyPath:
    """Tests for POST /api/chat happy path."""

    @patch("src.api.routes.ask_langgraph")
    def test_chat_returns_answer(self, mock_pipeline):
        """Chat endpoint returns a well-formed response for a valid question."""
        mock_pipeline.return_value = Answer(
            text="Tiền tiểu đường là tình trạng đường huyết cao hơn bình thường.",
            sources=[
                ChunkResult(content="...", source="diabetes_guide.pdf", score=0.92),
            ],
            is_refused=False,
            refuse_reason=None,
        )

        response = client.post(
            "/api/chat",
            json={"question": "Tiền tiểu đường là gì?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Tiền tiểu đường" in data["text"]


# ---------------------------------------------------------------------------
# /api/chat — refusal path tests (US2)
# ---------------------------------------------------------------------------


class TestChatRefusal:
    """Tests for POST /api/chat refusal path."""

    @patch("src.api.routes.ask_langgraph")
    def test_chat_refusal(self, mock_pipeline):
        """Chat endpoint returns is_refused=true with refuse_reason for unsafe questions."""
        mock_pipeline.return_value = Answer(
            text="Xin lỗi, tôi không thể kê đơn thuốc.",
            sources=[],
            is_refused=True,
            refuse_reason="PRESCRIPTION",
        )

        response = client.post(
            "/api/chat",
            json={"question": "Kê đơn Metformin cho tôi"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Xin lỗi, tôi không thể kê đơn thuốc."


# ---------------------------------------------------------------------------
# /api/chat — validation tests (US3)
# ---------------------------------------------------------------------------


class TestChatValidation:
    """Tests for POST /api/chat input validation."""

    def test_empty_body(self):
        """Empty JSON body returns HTTP 422."""
        response = client.post("/api/chat", json={})

        assert response.status_code == 422

    def test_missing_question_field(self):
        """Body without 'question' field returns HTTP 422."""
        response = client.post("/api/chat", json={"query": "test"})

        assert response.status_code == 422

    def test_empty_question(self):
        """Empty string question returns HTTP 422."""
        response = client.post("/api/chat", json={"question": ""})

        assert response.status_code == 422

    def test_question_too_long(self):
        """Question exceeding 2000 chars returns HTTP 422."""
        long_question = "a" * 2001
        response = client.post("/api/chat", json={"question": long_question})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Error handling tests (T019 — US7)
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for global exception handler."""

    @patch("src.api.routes.ask_langgraph")
    def test_pipeline_exception_returns_500(self, mock_pipeline):
        """Pipeline exception returns HTTP 500 with generic message, no stack trace."""
        mock_pipeline.side_effect = RuntimeError("LLM timeout")

        response = client.post(
            "/api/chat",
            json={"question": "Tiền tiểu đường là gì?"},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error. Please try again later."
        # Ensure no stack trace is leaked in the response
        assert "LLM timeout" not in str(data)
        assert "Traceback" not in str(data)

    @patch("src.api.routes.ask_langgraph")
    def test_qdrant_disconnect_returns_500(self, mock_pipeline):
        """Qdrant connection error returns HTTP 500 with generic message."""
        mock_pipeline.side_effect = ConnectionError("Qdrant unreachable")

        response = client.post(
            "/api/chat",
            json={"question": "HbA1c bình thường là bao nhiêu?"},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error. Please try again later."
        assert "Qdrant unreachable" not in str(data)


# ---------------------------------------------------------------------------
# CORS tests (US5)
# ---------------------------------------------------------------------------


class TestCORS:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Preflight CORS response includes appropriate Access-Control-Allow-Origin."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # With allow_credentials=True, CORS reflects the request Origin
        # instead of returning wildcard "*"
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin is not None
        assert allow_origin in ("*", "http://localhost:3000")


# ---------------------------------------------------------------------------
# Swagger UI test (US6)
# ---------------------------------------------------------------------------


class TestSwaggerUI:
    """Tests for Swagger UI availability."""

    def test_docs_accessible(self):
        """GET /docs returns HTTP 200 (Swagger UI)."""
        response = client.get("/docs")

        assert response.status_code == 200
