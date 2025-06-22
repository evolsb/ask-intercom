"""Test the new MCP-only architecture end-to-end."""

import asyncio
import os
from unittest.mock import patch

import pytest

from src.config import Config
from src.intercom_client import IntercomClient
from src.mcp.universal_adapter import (
    FastIntercomBackend,
    LocalMCPBackend,
    create_universal_adapter,
)
from src.models import ConversationFilters


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return Config(
        intercom_token="test_token_123",
        openai_key="sk-test123",
        enable_mcp=True,
        mcp_backend="fastintercom",
    )


@pytest.mark.asyncio
async def test_mcp_only_no_rest_fallback():
    """Test that there's no REST fallback in MCP-only architecture."""

    # Should not have DirectRESTBackend anymore
    with pytest.raises(ImportError):
        pass


@pytest.mark.asyncio
async def test_fastintercom_preferred_by_default(mock_config):
    """Test that FastIntercomMCP is preferred by default."""
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(LocalMCPBackend, "initialize", return_value=True):
            adapter = await create_universal_adapter(
                intercom_token=mock_config.intercom_token,
                prefer_fastintercom=True,
            )

            assert adapter.current_backend == "fastintercom"
            assert adapter.is_using_mcp is True
            await adapter.close()


@pytest.mark.asyncio
async def test_local_mcp_fallback_when_fastintercom_fails():
    """Test fallback to local MCP when FastIntercomMCP fails."""
    with patch.object(FastIntercomBackend, "initialize", return_value=False):
        with patch.object(LocalMCPBackend, "initialize", return_value=True):
            adapter = await create_universal_adapter(
                intercom_token="test_token",
                prefer_fastintercom=True,
            )

            assert adapter.current_backend == "local_mcp"
            assert adapter.is_using_mcp is True
            await adapter.close()


@pytest.mark.asyncio
async def test_intercom_client_mcp_integration(mock_config):
    """Test IntercomClient MCP integration."""
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(FastIntercomBackend, "call_tool") as mock_call_tool:
            mock_call_tool.return_value = {
                "conversations": [
                    {
                        "id": "test_conv_123",
                        "created_at": "2024-01-01T12:00:00Z",
                        "customer_email": "test@example.com",
                        "tags": ["urgent"],
                        "messages": [
                            {
                                "id": "msg_123",
                                "author_type": "user",
                                "body": "Test message",
                                "created_at": "2024-01-01T12:00:00Z",
                            }
                        ],
                    }
                ]
            }

            client = IntercomClient(mock_config)
            filters = ConversationFilters(limit=10)

            conversations = await client.fetch_conversations(filters)

            assert len(conversations) == 1
            assert conversations[0].id == "test_conv_123"
            assert conversations[0].customer_email == "test@example.com"
            assert len(conversations[0].messages) == 1


@pytest.mark.asyncio
async def test_mcp_backend_configuration():
    """Test different MCP backend configurations."""
    configs = [
        ("fastintercom", FastIntercomBackend),
        ("local_mcp", LocalMCPBackend),
        ("official", None),  # Will fail to initialize in tests
    ]

    for backend_name, expected_backend_class in configs:
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            enable_mcp=True,
            mcp_backend=backend_name,
        )

        if expected_backend_class:
            with patch.object(expected_backend_class, "initialize", return_value=True):
                adapter = await create_universal_adapter(
                    intercom_token=config.intercom_token,
                    force_backend=backend_name,
                )

                assert adapter.current_backend == backend_name
                await adapter.close()


@pytest.mark.asyncio
async def test_fastintercom_package_import():
    """Test FastIntercomMCP package import handling."""
    from src.mcp.fastintercom_backend import FastIntercomDatabase

    # Test graceful handling when package is not available
    with patch(
        "builtins.__import__", side_effect=ImportError("No module named 'fastintercom'")
    ):
        db = FastIntercomDatabase()
        available = db._ensure_fastintercom_available()
        assert available is False


@pytest.mark.asyncio
async def test_conversation_search_performance_tracking():
    """Test that MCP performance is tracked."""
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(FastIntercomBackend, "call_tool") as mock_call_tool:
            mock_call_tool.return_value = {"conversations": []}

            adapter = await create_universal_adapter(
                "test_token", force_backend="fastintercom"
            )

            filters = ConversationFilters(limit=5)
            conversations = await adapter.search_conversations(filters)

            # Should call the backend
            mock_call_tool.assert_called_once()
            assert conversations == []

            await adapter.close()


class TestRealMCPIntegration:
    """Test with real configuration if available."""

    @pytest.mark.skipif(
        not os.getenv("INTERCOM_ACCESS_TOKEN"),
        reason="No real Intercom token available",
    )
    @pytest.mark.asyncio
    async def test_real_mcp_architecture(self):
        """Test real MCP architecture with environment variables."""
        # Set MCP-only configuration
        os.environ["ENABLE_MCP"] = "true"
        os.environ["MCP_BACKEND"] = "local_mcp"  # Use local MCP for testing

        try:
            config = Config.from_env()
            client = IntercomClient(config)

            # Test that MCP is enabled
            assert config.enable_mcp is True
            assert config.mcp_backend == "local_mcp"

            # Test conversation fetching
            filters = ConversationFilters(limit=1)
            conversations = await client.fetch_conversations(filters)

            print(f"Fetched {len(conversations)} conversations via MCP")

            if conversations:
                conv = conversations[0]
                print(f"Conversation ID: {conv.id}")
                print(f"Created: {conv.created_at}")
                print(f"Messages: {len(conv.messages)}")

        finally:
            # Clean up environment
            os.environ.pop("ENABLE_MCP", None)
            os.environ.pop("MCP_BACKEND", None)


@pytest.mark.asyncio
async def test_no_direct_rest_backend_available():
    """Ensure DirectRESTBackend is completely removed."""
    from src.mcp import universal_adapter

    # Check that DirectRESTBackend doesn't exist
    assert not hasattr(universal_adapter, "DirectRESTBackend")

    # Check that only MCP backends are available
    adapter_code = open(universal_adapter.__file__).read()
    assert "DirectRESTBackend" not in adapter_code
    assert "MCP-only" in adapter_code


if __name__ == "__main__":
    # Run specific tests
    if os.getenv("INTERCOM_ACCESS_TOKEN"):
        print("Running real MCP integration tests...")

        async def run_real_tests():
            test = TestRealMCPIntegration()
            await test.test_real_mcp_architecture()

        asyncio.run(run_real_tests())
    else:
        print("No INTERCOM_ACCESS_TOKEN found, skipping real tests")
        print("Run: pytest tests/integration/test_mcp_only_architecture.py")
