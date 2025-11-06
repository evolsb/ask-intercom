"""
Simple end-to-end tests for the web application.

These tests verify the API works correctly without complex multiprocessing.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models import AnalysisResult, CostInfo, TimeFrame
from src.web.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_analysis_result():
    """Mock analysis result for testing."""
    return AnalysisResult(
        summary="Comprehensive customer feedback analysis",
        key_insights=[
            "Critical issue: Payment processing failures affecting 12% of transactions",
            "Feature request: Advanced search functionality requested by 28 customers",
            "Positive feedback: New dashboard design praised by 85% of users",
            "Performance concern: Page load times exceed 3 seconds for mobile users",
            "Support trend: Most common issues relate to account setup and billing",
        ],
        conversation_count=247,
        time_range=TimeFrame(
            start_date=datetime(2024, 6, 1),
            end_date=datetime(2024, 6, 18),
            description="last 2 weeks",
        ),
        cost_info=CostInfo(
            tokens_used=3421, estimated_cost_usd=0.58, model_used="gpt-4"
        ),
    )


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_health_and_status_endpoints(self, client):
        """Test that basic endpoints work correctly."""
        # Health check
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "Ask-Intercom API is running" in data["message"]

        # Status check
        response = client.get("/api/status")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "ask-intercom-api"
        assert data["version"] == "0.1.0"
        assert "environment" in data

    def test_missing_api_keys_error(self, client):
        """Test proper error handling when API keys are missing."""
        response = client.post(
            "/api/analyze", json={"query": "What are the top customer complaints?"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "Missing API keys" in data["detail"]

    def test_complete_analysis_workflow(self, client, mock_analysis_result):
        """Test the complete analysis workflow with realistic data."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            # Setup mock processor
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            # Test with a realistic customer support query
            response = client.post(
                "/api/analyze",
                json={
                    "query": "What are customers saying about our new payment system? Any issues or feedback?",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                    "max_conversations": 150,
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            required_fields = [
                "insights",
                "cost",
                "response_time_ms",
                "conversation_count",
            ]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Verify content quality
            assert len(data["insights"]) == 5
            assert "Payment processing failures" in data["insights"][0]
            assert "Advanced search functionality" in data["insights"][1]
            assert data["cost"] == 0.58
            assert data["conversation_count"] == 247
            assert data["response_time_ms"] >= 0

            # Verify processor was called correctly
            mock_processor.process_query.assert_called_once_with(
                "What are customers saying about our new payment system? Any issues or feedback?"
            )

    def test_various_query_types(self, client, mock_analysis_result):
        """Test different types of customer support queries."""
        query_scenarios = [
            {
                "query": "What bugs are customers reporting this week?",
                "expected_context": "bug reports and technical issues",
            },
            {
                "query": "Show me feature requests from enterprise customers",
                "expected_context": "feature enhancement requests",
            },
            {
                "query": "How satisfied are customers with our support response times?",
                "expected_context": "support quality and performance",
            },
            {
                "query": "What are the most common billing questions?",
                "expected_context": "billing and payment inquiries",
            },
        ]

        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            for scenario in query_scenarios:
                response = client.post(
                    "/api/analyze",
                    json={
                        "query": scenario["query"],
                        "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                        "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                        "max_conversations": 50,
                    },
                )

                assert (
                    response.status_code == 200
                ), f"Failed for query: {scenario['query']}"

                data = response.json()
                assert len(data["insights"]) > 0
                assert data["cost"] > 0
                assert data["conversation_count"] > 0

    def test_api_key_validation(self, client):
        """Test API key validation with various invalid formats."""
        invalid_key_scenarios = [
            {
                "intercom_token": "short",  # Too short
                "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                "expected_error": "Invalid Intercom access token",
            },
            {
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                "openai_key": "invalid-format",  # Wrong format
                "expected_error": "Invalid OpenAI API key",
            },
            {
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                "openai_key": "pk-wrong-prefix123456789012345678901234567890123456789012345678",
                "expected_error": "Invalid OpenAI API key",
            },
        ]

        for scenario in invalid_key_scenarios:
            response = client.post(
                "/api/analyze",
                json={
                    "query": "Test query",
                    "intercom_token": scenario["intercom_token"],
                    "openai_key": scenario["openai_key"],
                },
            )

            assert response.status_code == 500  # Config validation error
            data = response.json()
            assert scenario["expected_error"] in data["detail"]

    def test_conversation_limit_enforcement(self, client, mock_analysis_result):
        """Test that conversation limits are properly enforced."""
        with (
            patch("src.web.main.QueryProcessor") as mock_processor_class,
            patch("src.web.main.Config") as mock_config_class,
        ):
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            mock_config = AsyncMock()
            mock_config_class.return_value = mock_config

            # Test with limit over maximum (should be capped at 200)
            response = client.post(
                "/api/analyze",
                json={
                    "query": "Test limit enforcement",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                    "max_conversations": 500,
                },
            )

            assert response.status_code == 200

            # Verify Config was created with capped limit
            mock_config_class.assert_called_once()
            call_kwargs = mock_config_class.call_args[1]
            assert call_kwargs["max_conversations"] == 200

    def test_cors_functionality(self, client):
        """Test CORS headers for frontend integration."""
        # Test actual request with Origin header
        response = client.get(
            "/api/health", headers={"Origin": "http://localhost:5173"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

        # Test CORS preflight request
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

    def test_request_validation(self, client):
        """Test request validation for various error cases."""
        # Test malformed JSON
        response = client.post(
            "/api/analyze",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # Test missing required fields
        response = client.post(
            "/api/analyze",
            json={
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret"
                # Missing required 'query' field
            },
        )
        assert response.status_code == 422

        # Test empty query (should be allowed - backend decides)
        response = client.post(
            "/api/analyze",
            json={
                "query": "",
                "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
            },
        )
        assert response.status_code in [
            400,
            500,
        ]  # Should fail for missing keys or other validation

    def test_error_propagation(self, client):
        """Test that backend errors are properly propagated."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.side_effect = Exception(
                "Backend processing failed"
            )
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/api/analyze",
                json={
                    "query": "Test error handling",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                },
            )

            assert response.status_code == 500
            data = response.json()
            assert "Backend processing failed" in data["detail"]

    def test_realistic_performance_expectations(self, client, mock_analysis_result):
        """Test performance characteristics with realistic expectations."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            # Import time here to measure response time
            import time

            start_time = time.time()
            response = client.post(
                "/api/analyze",
                json={
                    "query": "Analyze customer satisfaction trends over the past month",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                    "max_conversations": 100,
                },
            )
            end_time = time.time()

            assert response.status_code == 200

            # With mocked backend, response should be very fast
            response_time = end_time - start_time
            assert response_time < 0.5  # Should be under 500ms with mocking

            # Verify response includes timing
            data = response.json()
            assert "response_time_ms" in data
            assert isinstance(data["response_time_ms"], int)
            assert data["response_time_ms"] >= 0


class TestDataQuality:
    """Test data quality and response formatting."""

    def test_response_data_formats(self, client, mock_analysis_result):
        """Test that response data is properly formatted."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/api/analyze",
                json={
                    "query": "Data format validation test",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=  # pragma: allowlist secret",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678  # pragma: allowlist secret",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Test data types
            assert isinstance(data["insights"], list)
            assert isinstance(data["cost"], (int, float))
            assert isinstance(data["response_time_ms"], int)
            assert isinstance(data["conversation_count"], int)

            # Test data quality
            assert len(data["insights"]) > 0
            assert all(isinstance(insight, str) for insight in data["insights"])
            assert all(len(insight.strip()) > 0 for insight in data["insights"])
            assert data["cost"] >= 0
            assert data["conversation_count"] >= 0
            assert data["response_time_ms"] >= 0


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
