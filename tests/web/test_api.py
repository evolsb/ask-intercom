"""Tests for the FastAPI web application."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models import AnalysisResult, CostInfo, TimeFrame


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Create a test app without static file mounting
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.web.main import (
        AnalysisResponse,
        HealthResponse,
        analyze_conversations,
        health_check,
        status,
    )

    test_app = FastAPI(title="Ask-Intercom API Test", version="0.1.0")

    # Add CORS
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add routes
    test_app.get("/api/health", response_model=HealthResponse)(health_check)
    test_app.get("/api/status", response_model=dict)(status)
    test_app.post("/api/analyze", response_model=AnalysisResponse)(
        analyze_conversations
    )

    return TestClient(test_app)


@pytest.fixture
def mock_analysis_result():
    """Mock analysis result for testing."""
    return AnalysisResult(
        summary="Analysis of customer conversations",
        key_insights=[
            "Top complaint: Slow response times mentioned 15 times",
            "Feature request: Dark mode requested by 8 customers",
            "Bug report: Login issues affecting mobile users",
        ],
        conversation_count=42,
        time_range=TimeFrame(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            description="this month",
        ),
        cost_info=CostInfo(
            tokens_used=1500, estimated_cost_usd=0.25, model_used="gpt-4"
        ),
    )


class TestHealthAndStatus:
    """Test health and status endpoints."""

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "Ask-Intercom API is running" in data["message"]

    def test_status_endpoint(self, client):
        """Test the status endpoint."""
        response = client.get("/api/status")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "ask-intercom-api"
        assert data["version"] == "0.1.0"
        assert "environment" in data
        assert "frontend_built" in data


class TestAnalysisEndpoint:
    """Test the main analysis endpoint."""

    def test_analyze_missing_api_keys(self, client):
        """Test analysis endpoint with missing API keys."""
        response = client.post(
            "/api/analyze", json={"query": "What are the top customer complaints?"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "Missing API keys" in data["detail"]

    def test_analyze_with_request_keys(self, client, mock_analysis_result):
        """Test analysis endpoint with API keys in request body."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            # Mock the processor instance and its process_query method
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/api/analyze",
                json={
                    "query": "What are the top customer complaints?",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",  # Valid length token  # pragma: allowlist secret
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",  # Valid SK key  # pragma: allowlist secret
                    "max_conversations": 25,
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "insights" in data
        assert "cost" in data
        assert "response_time_ms" in data
        assert "conversation_count" in data

        # Verify data transformation
        assert len(data["insights"]) == 3
        assert data["cost"] == 0.25
        assert data["response_time_ms"] >= 0  # Should be a valid time
        assert data["conversation_count"] == 42

    def test_analyze_with_env_keys(self, client, mock_analysis_result):
        """Test analysis endpoint with API keys from environment."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class, patch.dict(
            os.environ,
            {
                "INTERCOM_ACCESS_TOKEN": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                "OPENAI_API_KEY": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",  # pragma: allowlist secret
            },
        ):
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/api/analyze", json={"query": "What are the most requested features?"}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["insights"]) == 3

    def test_analyze_max_conversations_limit(self, client, mock_analysis_result):
        """Test that max_conversations is capped at 200."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class, patch(
            "src.web.main.Config"
        ) as mock_config_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            mock_config = MagicMock()
            mock_config_class.return_value = mock_config

            _ = client.post(
                "/api/analyze",
                json={
                    "query": "Test query",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                    "max_conversations": 500,  # Should be capped at 200
                },
            )

        # Verify Config was called with max 200
        mock_config_class.assert_called_once()
        call_kwargs = mock_config_class.call_args[1]
        assert call_kwargs["max_conversations"] == 200

    def test_analyze_processing_error(self, client):
        """Test handling of processing errors."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.side_effect = Exception("Processing failed")
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/api/analyze",
                json={
                    "query": "Test query",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                },
            )

        assert response.status_code == 500
        data = response.json()
        assert "Processing failed" in data["detail"]


class TestRequestValidation:
    """Test request validation and edge cases."""

    def test_analyze_empty_query(self, client):
        """Test analysis with empty query."""
        response = client.post(
            "/api/analyze",
            json={
                "query": "",
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
            },
        )

        # Should still accept empty query (let backend handle it)
        assert response.status_code in [200, 500]  # Depends on backend validation

    def test_analyze_invalid_json(self, client):
        """Test analysis with invalid JSON."""
        response = client.post(
            "/api/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_analyze_missing_required_fields(self, client):
        """Test analysis with missing required fields."""
        response = client.post(
            "/api/analyze",
            json={
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret"
                # Missing query field
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestCORSConfiguration:
    """Test CORS configuration for frontend integration."""

    def test_cors_preflight(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_actual_request(self, client):
        """Test actual request with CORS headers."""
        response = client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_full_analysis_workflow(self, client, mock_analysis_result):
        """Test a complete analysis workflow."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            # Simulate a realistic query
            response = client.post(
                "/api/analyze",
                json={
                    "query": "What are customers saying about our mobile app performance in the last week?",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                    "max_conversations": 75,
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Verify realistic response structure
        assert isinstance(data["insights"], list)
        assert len(data["insights"]) > 0
        assert data["cost"] > 0
        assert data["response_time_ms"] >= 0  # Mock execution can be very fast
        assert data["conversation_count"] > 0

        # Verify processor was called with correct query
        mock_processor.process_query.assert_called_once_with(
            "What are customers saying about our mobile app performance in the last week?"
        )
