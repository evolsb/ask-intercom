"""Test the Universal MCP Adapter functionality."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

from src.mcp.universal_adapter import (
    FastIntercomBackend,
    LocalMCPBackend,
    OfficialMCPBackend,
    UniversalMCPAdapter,
    create_universal_adapter,
)
from src.models import ConversationFilters


@pytest.fixture
def mock_token():
    """Mock Intercom token for testing."""
    return "test_token_123"


@pytest.mark.asyncio
async def test_universal_adapter_initialization(mock_token):
    """Test universal adapter initializes and selects backend."""
    # Mock FastIntercomMCP to succeed, others to fail
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(OfficialMCPBackend, "initialize", return_value=False):
            with patch.object(LocalMCPBackend, "initialize", return_value=True):
                adapter = UniversalMCPAdapter(mock_token)
                await adapter.initialize()

                # Should select FastIntercomMCP as preferred
                assert adapter.current_backend == "fastintercom"
                assert adapter.is_using_mcp is True
                assert "fastintercom" in adapter.available_backends
                assert "local_mcp" in adapter.available_backends


@pytest.mark.asyncio
async def test_force_backend_selection(mock_token):
    """Test forcing specific backend."""
    with patch.object(LocalMCPBackend, "initialize", return_value=True):
        adapter = UniversalMCPAdapter(mock_token, force_backend="local_mcp")
        await adapter.initialize()

        assert adapter.current_backend == "local_mcp"
        assert adapter.is_using_mcp is True


@pytest.mark.asyncio
async def test_backend_switching(mock_token):
    """Test switching between backends at runtime."""
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(LocalMCPBackend, "initialize", return_value=True):
            adapter = UniversalMCPAdapter(mock_token)
            await adapter.initialize()

            # Should start with FastIntercomMCP
            assert adapter.current_backend == "fastintercom"

            # Switch to local MCP
            await adapter.switch_backend("local_mcp")
            assert adapter.current_backend == "local_mcp"


@pytest.mark.asyncio
async def test_search_conversations_local_mcp(mock_token):
    """Test search conversations via local MCP."""
    mock_result = {
        "conversations": [{"id": "123", "state": "open", "created_at": 1640995200}]
    }

    with patch.object(LocalMCPBackend, "initialize", return_value=True):
        with patch.object(LocalMCPBackend, "call_tool", return_value=mock_result):
            adapter = UniversalMCPAdapter(mock_token, force_backend="local_mcp")
            await adapter.initialize()

            filters = ConversationFilters(limit=10)
            conversations = await adapter.search_conversations(filters)

            assert len(conversations) == 1
            assert conversations[0].id == "123"


@pytest.mark.asyncio
async def test_search_conversations_fastintercom(mock_token):
    """Test search conversations via FastIntercomMCP."""
    mock_result = {
        "conversations": [
            {
                "id": "456",
                "created_at": "2021-12-31T12:00:00Z",
                "customer_email": "test@example.com",
                "tags": [],
                "messages": [],
            }
        ]
    }

    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(FastIntercomBackend, "call_tool", return_value=mock_result):
            adapter = UniversalMCPAdapter(mock_token, force_backend="fastintercom")
            await adapter.initialize()

            filters = ConversationFilters(limit=5)
            conversations = await adapter.search_conversations(filters)

            assert len(conversations) == 1
            assert conversations[0].id == "456"


@pytest.mark.asyncio
async def test_fastintercom_preferred_when_working(mock_token):
    """Test that FastIntercomMCP is selected when it works."""
    with patch.object(FastIntercomBackend, "initialize", return_value=True):
        with patch.object(OfficialMCPBackend, "initialize", return_value=True):
            with patch.object(LocalMCPBackend, "initialize", return_value=True):
                adapter = UniversalMCPAdapter(mock_token, prefer_fastintercom=True)
                await adapter.initialize()

                # Should select FastIntercomMCP when it works
                assert adapter.current_backend == "fastintercom"


@pytest.mark.asyncio
async def test_factory_function(mock_token):
    """Test the factory function."""
    with patch.object(LocalMCPBackend, "initialize", return_value=True):
        adapter = await create_universal_adapter(mock_token)

        assert adapter.current_backend in ["local_mcp", "direct_rest"]
        await adapter.close()


@pytest.mark.asyncio
async def test_error_handling(mock_token):
    """Test error handling when all backends fail."""
    with patch.object(FastIntercomBackend, "initialize", return_value=False):
        with patch.object(OfficialMCPBackend, "initialize", return_value=False):
            with patch.object(LocalMCPBackend, "initialize", return_value=False):
                adapter = UniversalMCPAdapter(mock_token)

                with pytest.raises(Exception, match="No functional backend available"):
                    await adapter.initialize()


@pytest.mark.asyncio
async def test_cleanup(mock_token):
    """Test proper cleanup of backends."""
    mock_close = AsyncMock()

    with patch.object(LocalMCPBackend, "initialize", return_value=True):
        with patch.object(LocalMCPBackend, "close", mock_close):
            adapter = UniversalMCPAdapter(mock_token)
            await adapter.initialize()
            await adapter.close()

            mock_close.assert_called_once()


class TestRealIntercomIntegration:
    """Test with real Intercom token if available."""

    @pytest.mark.skipif(
        not os.getenv("INTERCOM_ACCESS_TOKEN"),
        reason="No real Intercom token available",
    )
    @pytest.mark.asyncio
    async def test_real_adapter_initialization(self):
        """Test adapter with real Intercom token."""
        token = os.getenv("INTERCOM_ACCESS_TOKEN")

        adapter = await create_universal_adapter(token)

        # Should have at least local MCP working
        assert adapter.current_backend in ["fastintercom", "local_mcp"]
        print(f"Selected backend: {adapter.current_backend}")
        print(f"Available backends: {list(adapter.available_backends.keys())}")

        await adapter.close()

    @pytest.mark.skipif(
        not os.getenv("INTERCOM_ACCESS_TOKEN"),
        reason="No real Intercom token available",
    )
    @pytest.mark.asyncio
    async def test_real_search_conversations(self):
        """Test real conversation search."""
        token = os.getenv("INTERCOM_ACCESS_TOKEN")

        adapter = await create_universal_adapter(token)

        filters = ConversationFilters(limit=1)
        conversations = await adapter.search_conversations(filters)

        print(
            f"Found {len(conversations)} conversations using {adapter.current_backend}"
        )

        if conversations:
            conv = conversations[0]
            print(f"Conversation ID: {conv.id}")
            print(f"State: {conv.state}")
            print(f"Created: {conv.created_at}")

        await adapter.close()


if __name__ == "__main__":
    # Run real integration tests if token is available
    if os.getenv("INTERCOM_ACCESS_TOKEN"):
        print("Running real integration tests...")

        async def run_real_tests():
            test = TestRealIntercomIntegration()
            await test.test_real_adapter_initialization()
            await test.test_real_search_conversations()

        asyncio.run(run_real_tests())
    else:
        print("No INTERCOM_ACCESS_TOKEN found, skipping real tests")
        print("Set environment variable to test with real Intercom API")
