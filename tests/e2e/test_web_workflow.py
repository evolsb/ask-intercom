"""
End-to-end tests for the web application workflow.

These tests verify the complete user journey from API key setup to getting results.
"""

import time
from datetime import datetime
from multiprocessing import Process
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import uvicorn

from src.models import AnalysisResult, CostInfo, TimeFrame
from src.web.main import app


class WebAppTestServer:
    """Test server for end-to-end testing."""

    def __init__(self, port=8001):
        self.port = port
        self.process = None
        self.base_url = f"http://localhost:{port}"

    def start(self):
        """Start the test server."""

        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=self.port, log_level="error")

        self.process = Process(target=run_server)
        self.process.start()

        # Wait for server to start
        for _ in range(30):  # 3 second timeout
            try:
                import requests

                response = requests.get(f"{self.base_url}/api/health", timeout=1)
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            raise Exception("Server failed to start")

    def stop(self):
        """Stop the test server."""
        if self.process:
            self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.kill()


@pytest.fixture(scope="module")
def test_server():
    """Start and stop test server for the module."""
    server = WebAppTestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def mock_analysis_result():
    """Mock analysis result for testing."""
    return AnalysisResult(
        summary="Analysis of customer conversations",
        key_insights=[
            "Top complaint: Response time issues mentioned 23 times",
            "Feature request: Mobile app improvements requested by 15 customers",
            "Positive feedback: Users love the new dashboard design",
            "Bug report: Payment processing errors affecting 8% of transactions",
        ],
        conversation_count=156,
        time_range=TimeFrame(
            start_date=datetime(2024, 6, 1),
            end_date=datetime(2024, 6, 18),
            description="last 2 weeks",
        ),
        cost_info=CostInfo(
            tokens_used=2847, estimated_cost_usd=0.42, model_used="gpt-4"
        ),
    )


class TestWebAppWorkflow:
    """Test complete web application workflows."""

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, test_server):
        """Test that health check endpoint works."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_server.base_url}/api/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "Ask-Intercom API is running" in data["message"]

    @pytest.mark.asyncio
    async def test_status_endpoint(self, test_server):
        """Test that status endpoint works."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_server.base_url}/api/status")
            assert response.status_code == 200

            data = response.json()
            assert data["service"] == "ask-intercom-api"
            assert data["version"] == "0.1.0"
            assert "environment" in data

    @pytest.mark.asyncio
    async def test_missing_api_keys_workflow(self, test_server):
        """Test the workflow when API keys are missing."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{test_server.base_url}/api/analyze",
                json={"query": "What are the top customer complaints?"},
                timeout=10.0,
            )

            assert response.status_code == 400
            data = response.json()
            assert "Missing API keys" in data["detail"]

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, test_server, mock_analysis_result):
        """Test complete analysis workflow with mocked backend."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            # Mock the processor
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            async with httpx.AsyncClient() as client:
                # Test the complete workflow
                analyze_response = await client.post(
                    f"{test_server.base_url}/api/analyze",
                    json={
                        "query": "What are customers saying about our product this month?",
                        "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=",
                        "openai_key": "sk-test123456789012345678901234567890123456789012345678",
                        "max_conversations": 100,
                    },
                    timeout=10.0,
                )

                assert response.status_code == 200
                data = response.json()

                # Verify response structure
                assert "insights" in data
                assert "cost" in data
                assert "response_time_ms" in data
                assert "conversation_count" in data

                # Verify content
                assert len(data["insights"]) == 4
                assert "Response time issues" in data["insights"][0]
                assert "Mobile app improvements" in data["insights"][1]
                assert data["cost"] == 0.42
                assert data["conversation_count"] == 156
                assert data["response_time_ms"] >= 0

                # Verify the processor was called correctly
                mock_processor.process_query.assert_called_once_with(
                    "What are customers saying about our product this month?"
                )

    @pytest.mark.asyncio
    async def test_realistic_query_scenarios(self, test_server, mock_analysis_result):
        """Test realistic user query scenarios."""
        test_queries = [
            "What are the top customer complaints this week?",
            "Show me feature requests from the last month",
            "What bugs are customers reporting?",
            "How do customers feel about our new feature?",
            "What are the most common support issues?",
        ]

        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            async with httpx.AsyncClient() as client:
                for query in test_queries:
                    analyze_response = await client.post(
                        f"{test_server.base_url}/api/analyze",
                        json={
                            "query": query,
                            "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=",
                            "openai_key": "sk-test123456789012345678901234567890123456789012345678",
                            "max_conversations": 50,
                        },
                        timeout=10.0,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["insights"]) > 0
                    assert data["cost"] > 0
                    assert data["conversation_count"] > 0

    @pytest.mark.asyncio
    async def test_invalid_api_keys_workflow(self, test_server):
        """Test workflow with invalid API keys."""
        async with httpx.AsyncClient() as client:
            # Test with invalid Intercom token (too short)
            response = await client.post(
                f"{test_server.base_url}/api/analyze",
                json={
                    "query": "Test query",
                    "intercom_token": "short",
                    "openai_key": "sk-test123456789012345678901234567890123456789012345678",
                },
                timeout=10.0,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Invalid Intercom access token" in data["detail"]

            # Test with invalid OpenAI key (wrong format)
            response = await client.post(
                f"{test_server.base_url}/api/analyze",
                json={
                    "query": "Test query",
                    "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=",
                    "openai_key": "invalid-key-format",
                },
                timeout=10.0,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Invalid OpenAI API key" in data["detail"]

    @pytest.mark.asyncio
    async def test_max_conversations_limit(self, test_server, mock_analysis_result):
        """Test that max conversations is properly limited."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class, patch(
            "src.web.main.Config"
        ) as mock_config_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            mock_config = AsyncMock()
            mock_config_class.return_value = mock_config

            async with httpx.AsyncClient() as client:
                analyze_response = await client.post(
                    f"{test_server.base_url}/api/analyze",
                    json={
                        "query": "Test query",
                        "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=",
                        "openai_key": "sk-test123456789012345678901234567890123456789012345678",
                        "max_conversations": 500,  # Should be capped at 200
                    },
                    timeout=10.0,
                )

                # Verify Config was called with capped value
                mock_config_class.assert_called_once()
                call_kwargs = mock_config_class.call_args[1]
                assert call_kwargs["max_conversations"] == 200

    @pytest.mark.asyncio
    async def test_cors_headers(self, test_server):
        """Test that CORS headers are properly set."""
        async with httpx.AsyncClient() as client:
            # Test CORS headers on health endpoint
            response = await client.get(
                f"{test_server.base_url}/api/health",
                headers={"Origin": "http://localhost:5173"},
            )

            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

            # Test CORS preflight
            response = await client.request(
                "OPTIONS",
                f"{test_server.base_url}/api/analyze",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, test_server):
        """Test error handling in various scenarios."""
        async with httpx.AsyncClient() as client:
            # Test malformed JSON
            response = await client.post(
                f"{test_server.base_url}/api/analyze",
                content="invalid json",
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )

            assert response.status_code == 422  # Unprocessable Entity

            # Test missing required fields
            response = await client.post(
                f"{test_server.base_url}/api/analyze",
                json={"intercom_token": "test"},  # Missing query
                timeout=10.0,
            )

            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_performance_characteristics(self, test_server, mock_analysis_result):
        """Test performance characteristics of the API."""
        with patch("src.web.main.QueryProcessor") as mock_processor_class:
            mock_processor = AsyncMock()
            mock_processor.process_query.return_value = mock_analysis_result
            mock_processor_class.return_value = mock_processor

            async with httpx.AsyncClient() as client:
                # Test response time
                start_time = time.time()
                analyze_response = await client.post(
                    f"{test_server.base_url}/api/analyze",
                    json={
                        "query": "Performance test query",
                        "intercom_token": "dG9rZW5fZXhhbXBsZTEyMzQ1Njc4OTA=",
                        "openai_key": "sk-test123456789012345678901234567890123456789012345678",
                    },
                    timeout=10.0,
                )
                end_time = time.time()

                assert response.status_code == 200

                # API should respond quickly (mocked backend)
                response_time = end_time - start_time
                assert response_time < 1.0  # Should be under 1 second with mocking

                # Verify response includes timing information
                data = response.json()
                assert "response_time_ms" in data
                assert isinstance(data["response_time_ms"], int)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
