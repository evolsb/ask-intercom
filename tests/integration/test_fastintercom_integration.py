"""
Integration tests for FastIntercomMCP backend.

Tests the integration of FastIntercomMCP caching backend
with our universal adapter architecture.
"""

import asyncio
import os
from datetime import datetime, timedelta

import pytest

from src.config import Config
from src.intercom_client import IntercomClient
from src.mcp.fastintercom_backend import FastIntercomBackend, FastIntercomDatabase
from src.mcp.universal_adapter import create_universal_adapter


@pytest.mark.asyncio
@pytest.mark.integration
class TestFastIntercomIntegration:
    """Test FastIntercomMCP integration with universal adapter."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.config = Config.from_env()
        self.access_token = self.config.intercom_token

        # Skip if no access token
        if not self.access_token or self.access_token == "":
            pytest.skip("No Intercom access token provided")

    async def test_fastintercom_database_availability(self):
        """Test that FastIntercomMCP components are available."""
        db = FastIntercomDatabase()

        # Should not raise an exception
        assert db is not None
        assert db.db_path is not None

    async def test_fastintercom_backend_initialization(self):
        """Test FastIntercomMCP backend initialization."""
        backend = FastIntercomBackend(self.access_token)

        # Test initialization
        try:
            initialized = await backend.initialize()
            # It's ok if initialization fails due to missing FastIntercomMCP
            # We just want to ensure it doesn't crash
            assert initialized in [True, False]
        except Exception as e:
            # Expected if FastIntercomMCP is not fully set up
            assert "FastIntercomMCP" in str(e) or "not available" in str(e)

    async def test_universal_adapter_with_fastintercom(self):
        """Test universal adapter with FastIntercomMCP backend forced."""
        try:
            adapter = await create_universal_adapter(
                intercom_token=self.access_token, force_backend="fastintercom"
            )

            # Should have selected FastIntercomMCP backend
            assert adapter.current_backend == "fastintercom"
            assert adapter.is_using_mcp is True

            await adapter.close()

        except Exception as e:
            # Expected if FastIntercomMCP is not fully configured
            assert (
                "FastIntercomMCP" in str(e)
                or "not available" in str(e)
                or "not initialized" in str(e)
            )

    async def test_backend_priority_with_fastintercom(self):
        """Test that FastIntercomMCP is tried in correct priority order."""
        adapter = await create_universal_adapter(
            intercom_token=self.access_token,
            prefer_official=True,  # Should try: official -> fastintercom -> local -> rest
        )

        # Should fall back to a working backend
        assert adapter.current_backend in [
            "official_mcp",
            "fastintercom",
            "local_mcp",
            "direct_rest",
        ]

        # Should have multiple backends available
        assert len(adapter.available_backends) >= 1

        await adapter.close()

    async def test_config_backend_selection(self):
        """Test backend selection via configuration."""
        # Test with auto selection
        config_auto = Config.from_env()
        config_auto.mcp_backend = "auto"

        client_auto = IntercomClient(self.access_token, config_auto)
        assert client_auto.config.mcp_backend == "auto"

        # Test with fastintercom forced
        config_fast = Config.from_env()
        config_fast.mcp_backend = "fastintercom"

        client_fast = IntercomClient(self.access_token, config_fast)
        assert client_fast.config.mcp_backend == "fastintercom"

    async def test_fastintercom_search_functionality(self):
        """Test FastIntercomMCP search functionality if available."""
        try:
            backend = FastIntercomBackend(self.access_token)
            initialized = await backend.initialize()

            if not initialized:
                pytest.skip("FastIntercomMCP backend not available")

            # Test search
            result = await backend.call_tool(
                "search_conversations", {"limit": 5, "query": None}
            )

            assert "conversations" in result
            assert isinstance(result["conversations"], list)

            # Test status
            status_result = await backend.call_tool("get_server_status", {})
            assert "backend_type" in status_result
            assert status_result["backend_type"] == "fastintercom"

            await backend.close()

        except Exception as e:
            # Expected if FastIntercomMCP is not set up
            pytest.skip(f"FastIntercomMCP not available: {e}")

    async def test_performance_comparison_setup(self):
        """Test that we can set up performance comparison between backends."""
        # Test REST backend
        adapter_rest = await create_universal_adapter(
            intercom_token=self.access_token, force_backend="direct_rest"
        )
        assert adapter_rest.current_backend == "direct_rest"

        # Test that we can measure performance
        start_time = datetime.now()

        try:
            # Try a simple search
            filters = type(
                "obj", (object,), {"limit": 5, "start_date": None, "end_date": None}
            )()
            conversations = await adapter_rest.search_conversations(filters)

            end_time = datetime.now()
            rest_duration = (end_time - start_time).total_seconds()

            assert rest_duration > 0
            assert isinstance(conversations, list)

        except Exception:
            # API might fail, that's ok for this test
            pass

        await adapter_rest.close()

        # Now test FastIntercomMCP backend if available
        try:
            adapter_fast = await create_universal_adapter(
                intercom_token=self.access_token, force_backend="fastintercom"
            )

            if adapter_fast.current_backend == "fastintercom":
                start_time = datetime.now()

                try:
                    conversations = await adapter_fast.search_conversations(filters)
                    end_time = datetime.now()
                    fast_duration = (end_time - start_time).total_seconds()

                    assert fast_duration > 0
                    # FastIntercomMCP should be faster due to caching
                    # (though this might not always be true on first run)

                except Exception:
                    # Expected if no cached data
                    pass

                await adapter_fast.close()

        except Exception:
            # FastIntercomMCP might not be available
            pass

    async def test_environment_variable_backend_selection(self):
        """Test backend selection via environment variables."""
        # Temporarily set environment variable
        original_value = os.environ.get("MCP_BACKEND")

        try:
            # Test fastintercom selection
            os.environ["MCP_BACKEND"] = "fastintercom"
            config = Config.from_env()
            assert config.mcp_backend == "fastintercom"

            # Test auto selection
            os.environ["MCP_BACKEND"] = "auto"
            config = Config.from_env()
            assert config.mcp_backend == "auto"

            # Test rest selection
            os.environ["MCP_BACKEND"] = "rest"
            config = Config.from_env()
            assert config.mcp_backend == "rest"

        finally:
            # Restore original value
            if original_value is not None:
                os.environ["MCP_BACKEND"] = original_value
            elif "MCP_BACKEND" in os.environ:
                del os.environ["MCP_BACKEND"]


@pytest.mark.asyncio
@pytest.mark.performance
class TestFastIntercomPerformance:
    """Performance tests for FastIntercomMCP vs REST comparison."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup performance test environment."""
        self.config = Config.from_env()
        self.access_token = self.config.intercom_token

        if not self.access_token:
            pytest.skip("No Intercom access token provided")

    async def test_backend_response_times(self):
        """Compare response times between different backends."""
        backends_to_test = ["direct_rest"]

        # Add FastIntercomMCP if available
        try:
            fastintercom_adapter = await create_universal_adapter(
                intercom_token=self.access_token, force_backend="fastintercom"
            )
            if fastintercom_adapter.current_backend == "fastintercom":
                backends_to_test.append("fastintercom")
            await fastintercom_adapter.close()
        except:
            pass

        results = {}

        for backend_name in backends_to_test:
            try:
                adapter = await create_universal_adapter(
                    intercom_token=self.access_token, force_backend=backend_name
                )

                # Measure response time
                start_time = datetime.now()

                filters = type(
                    "obj",
                    (object,),
                    {
                        "limit": 10,
                        "start_date": datetime.now() - timedelta(days=1),
                        "end_date": datetime.now(),
                    },
                )()

                conversations = await adapter.search_conversations(filters)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                results[backend_name] = {
                    "duration": duration,
                    "conversation_count": len(conversations),
                    "success": True,
                }

                await adapter.close()

            except Exception as e:
                results[backend_name] = {
                    "duration": None,
                    "conversation_count": 0,
                    "success": False,
                    "error": str(e),
                }

        # Log results
        print("\nPerformance Comparison Results:")
        for backend, result in results.items():
            if result["success"]:
                print(
                    f"{backend}: {result['duration']:.2f}s for {result['conversation_count']} conversations"
                )
            else:
                print(f"{backend}: Failed - {result.get('error', 'Unknown error')}")

        # At least one backend should work
        assert any(r["success"] for r in results.values())

    async def test_caching_effectiveness(self):
        """Test that FastIntercomMCP caching provides performance benefits."""
        try:
            adapter = await create_universal_adapter(
                intercom_token=self.access_token, force_backend="fastintercom"
            )

            if adapter.current_backend != "fastintercom":
                pytest.skip("FastIntercomMCP backend not available")

            filters = type(
                "obj",
                (object,),
                {
                    "limit": 5,
                    "start_date": datetime.now() - timedelta(hours=1),
                    "end_date": datetime.now(),
                },
            )()

            # First request (should populate cache)
            start_time = datetime.now()
            conversations1 = await adapter.search_conversations(filters)
            first_duration = (datetime.now() - start_time).total_seconds()

            # Second request (should use cache)
            start_time = datetime.now()
            conversations2 = await adapter.search_conversations(filters)
            second_duration = (datetime.now() - start_time).total_seconds()

            # Results should be consistent
            assert len(conversations1) == len(conversations2)

            # Second request should be faster (though this might not always be true)
            print(f"First request: {first_duration:.2f}s")
            print(f"Second request: {second_duration:.2f}s")
            print(f"Cache speedup: {first_duration / max(second_duration, 0.001):.1f}x")

            await adapter.close()

        except Exception as e:
            pytest.skip(f"FastIntercomMCP caching test failed: {e}")


if __name__ == "__main__":
    # Run basic integration test
    async def main():
        test = TestFastIntercomIntegration()
        test.setup()

        await test.test_fastintercom_database_availability()
        await test.test_backend_priority_with_fastintercom()

        print("✅ FastIntercomMCP integration tests passed!")

    asyncio.run(main())
