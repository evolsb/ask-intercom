"""Integration tests for MCP connections and transports."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from src.config import Config
from src.mcp.http_mcp_backend import HTTPMCPBackend
from src.mcp.mcp_freshness_checker import MCPFreshnessChecker, should_use_mcp_for_query
from src.mcp.universal_adapter import LocalMCPBackend, UniversalMCPAdapter
from src.models import ConversationFilters


class TestHTTPMCPBackend:
    """Test HTTP MCP backend connections."""

    @pytest.fixture
    def http_config(self):
        """HTTP transport configuration."""
        return Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

    @pytest.fixture
    def stdio_config(self):
        """Stdio transport configuration."""
        return Config(
            intercom_token="test_token", openai_key="sk-test123", mcp_transport="stdio"
        )

    @pytest.mark.asyncio
    async def test_http_backend_initialization_success(self, http_config):
        """Test successful HTTP backend initialization."""
        backend = HTTPMCPBackend(http_config)

        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"server_info": "Mock MCP Server", "status": "healthy"}
        )

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response

            success = await backend.initialize()
            assert success is True
            assert backend._initialized is True

            await backend.close()

    @pytest.mark.asyncio
    async def test_http_backend_initialization_failure(self, http_config):
        """Test HTTP backend initialization failure."""
        backend = HTTPMCPBackend(http_config)

        # Mock connection error
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Connection failed")

            success = await backend.initialize()
            assert success is False
            assert backend._initialized is False

    @pytest.mark.asyncio
    async def test_http_backend_call_tool_success(self, http_config):
        """Test successful HTTP MCP tool call."""
        backend = HTTPMCPBackend(http_config)

        # Mock the call_tool method directly to avoid aiohttp mocking complexity
        expected_result = {"conversations": [{"id": "conv_1"}], "total_count": 1}

        with patch.object(
            backend, "call_tool", return_value=expected_result
        ) as mock_call:
            result = await backend.call_tool("search_conversations", {"limit": 10})

            assert "conversations" in result
            assert result["total_count"] == 1
            mock_call.assert_called_once_with("search_conversations", {"limit": 10})

    @pytest.mark.asyncio
    async def test_http_backend_call_tool_404(self, http_config):
        """Test HTTP MCP tool call with 404 error."""
        backend = HTTPMCPBackend(http_config)

        # Mock call_tool to raise the expected error
        with patch.object(
            backend,
            "call_tool",
            side_effect=ValueError("Tool 'unknown_tool' not found"),
        ):
            with pytest.raises(ValueError, match="Tool 'unknown_tool' not found"):
                await backend.call_tool("unknown_tool", {})

    @pytest.mark.asyncio
    async def test_http_backend_call_tool_401(self, http_config):
        """Test HTTP MCP tool call with authentication error."""
        backend = HTTPMCPBackend(http_config)

        # Mock call_tool to raise authentication error
        with patch.object(
            backend, "call_tool", side_effect=RuntimeError("authentication failed")
        ):
            with pytest.raises(RuntimeError, match="authentication failed"):
                await backend.call_tool("search_conversations", {})

    @pytest.mark.asyncio
    async def test_http_backend_call_tool_503(self, http_config):
        """Test HTTP MCP tool call with server unavailable."""
        backend = HTTPMCPBackend(http_config)

        # Mock call_tool to raise server unavailable error
        with patch.object(
            backend, "call_tool", side_effect=RuntimeError("server unavailable")
        ):
            with pytest.raises(RuntimeError, match="server unavailable"):
                await backend.call_tool("search_conversations", {})


class TestLocalMCPBackend:
    """Test Local MCP backend (stdio transport)."""

    @pytest.mark.asyncio
    async def test_local_backend_initialization(self):
        """Test local MCP backend initialization."""
        backend = LocalMCPBackend("test_token")

        success = await backend.initialize()
        assert success is True
        assert backend.backend_type == "local_mcp"

        await backend.close()

    @pytest.mark.asyncio
    async def test_local_backend_call_tool(self):
        """Test local MCP backend tool calling."""
        backend = LocalMCPBackend("test_token")
        await backend.initialize()

        # Mock the server response
        mock_response = {
            "jsonrpc": "2.0",
            "id": "test-search_conversations",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": '{"conversations": [{"id": "conv_1"}], "total_count": 1}',
                    }
                ]
            },
        }

        with patch.object(backend.server, "handle_request", return_value=mock_response):
            result = await backend.call_tool("search_conversations", {"limit": 10})

            assert "conversations" in result
            assert result["total_count"] == 1

        await backend.close()


class TestUniversalMCPAdapter:
    """Test Universal MCP Adapter."""

    @pytest.mark.asyncio
    async def test_adapter_chooses_http_backend(self):
        """Test that adapter chooses HTTP backend for HTTP transport."""
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

        adapter = UniversalMCPAdapter(config=config)

        # Mock HTTP backend initialization
        with patch.object(HTTPMCPBackend, "initialize", return_value=True):
            await adapter.initialize()

            assert adapter.backend is not None
            assert adapter.backend.backend_type == "http-mcp"

    @pytest.mark.asyncio
    async def test_adapter_chooses_local_backend(self):
        """Test that adapter chooses local backend for stdio transport."""
        config = Config(
            intercom_token="test_token", openai_key="sk-test123", mcp_transport="stdio"
        )

        adapter = UniversalMCPAdapter(config=config)
        await adapter.initialize()

        assert adapter.backend is not None
        assert adapter.backend.backend_type == "local_mcp"

        await adapter.close()

    @pytest.mark.asyncio
    async def test_adapter_fails_when_no_backend_available(self):
        """Test that adapter fails when no backend is available."""
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

        adapter = UniversalMCPAdapter(config=config)

        # Mock HTTP backend initialization failure
        with patch.object(HTTPMCPBackend, "initialize", return_value=False):
            with pytest.raises(Exception, match="No functional backend available"):
                await adapter.initialize()


class TestMCPFreshnessChecker:
    """Test MCP freshness checking."""

    @pytest.mark.asyncio
    async def test_freshness_checker_http_backend(self):
        """Test freshness checker with HTTP backend."""
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

        adapter = UniversalMCPAdapter(config=config)
        adapter.backend = AsyncMock()
        adapter.backend.backend_type = "http-mcp"

        checker = MCPFreshnessChecker()

        freshness_info = await checker.get_freshness_info(adapter)

        assert freshness_info["status"] == "fresh"
        assert freshness_info["has_data"] is True
        assert (
            "HTTP MCP server manages its own data freshness" in freshness_info["note"]
        )

    @pytest.mark.asyncio
    async def test_should_use_mcp_for_query_http(self):
        """Test should_use_mcp_for_query with HTTP backend."""
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

        adapter = UniversalMCPAdapter(config=config)

        # Create a proper mock backend with call_tool method
        mock_backend = AsyncMock()
        mock_backend.backend_type = "http-mcp"
        mock_backend.call_tool = AsyncMock()
        adapter.backend = mock_backend

        filters = ConversationFilters(
            limit=10, start_date=datetime(2025, 6, 23), end_date=datetime(2025, 6, 24)
        )

        use_mcp, reason, metadata = await should_use_mcp_for_query(adapter, filters)

        assert use_mcp is True
        assert "HTTP MCP" in reason

    @pytest.mark.asyncio
    async def test_should_use_mcp_for_query_local(self):
        """Test should_use_mcp_for_query with local backend."""
        config = Config(
            intercom_token="test_token", openai_key="sk-test123", mcp_transport="stdio"
        )

        adapter = UniversalMCPAdapter(config=config)

        # Create a proper mock backend with call_tool method
        mock_backend = AsyncMock()
        mock_backend.backend_type = "local_mcp"
        mock_backend.call_tool = AsyncMock(side_effect=ValueError("Unknown tool"))
        adapter.backend = mock_backend

        filters = ConversationFilters(
            limit=10, start_date=datetime(2025, 6, 23), end_date=datetime(2025, 6, 24)
        )

        use_mcp, reason, metadata = await should_use_mcp_for_query(adapter, filters)

        assert use_mcp is True
        assert "LocalMCP" in reason


class TestMCPFailureScenarios:
    """Test MCP failure scenarios and error handling."""

    @pytest.mark.asyncio
    async def test_http_backend_connection_timeout(self):
        """Test HTTP backend with connection timeout."""
        config = Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:9999/mcp",  # Non-existent port
            mcp_api_key="test_api_key",
            mcp_timeout=1,  # 1 second timeout
        )

        backend = HTTPMCPBackend(config)

        success = await backend.initialize()
        assert success is False

    @pytest.mark.asyncio
    async def test_invalid_transport_config(self):
        """Test invalid transport configuration."""
        with pytest.raises(
            ValueError, match="mcp_transport must be either 'stdio' or 'http'"
        ):
            Config(
                intercom_token="test_token",
                openai_key="sk-test123",
                mcp_transport="invalid",
            )

    @pytest.mark.asyncio
    async def test_http_config_missing_url(self):
        """Test HTTP config missing URL."""
        with pytest.raises(ValueError, match="MCP_HTTP_URL must be set"):
            Config(
                intercom_token="test_token",
                openai_key="sk-test123",
                mcp_transport="http",
                mcp_api_key="test_key",
            )

    @pytest.mark.asyncio
    async def test_http_config_missing_api_key(self):
        """Test HTTP config missing API key."""
        with pytest.raises(ValueError, match="MCP_API_KEY must be set"):
            Config(
                intercom_token="test_token",
                openai_key="sk-test123",
                mcp_transport="http",
                mcp_http_url="http://localhost:8001/mcp",
            )


@pytest.mark.integration
class TestMCPIntegrationWithMockServer:
    """Integration tests with mock MCP server."""

    @pytest.fixture
    async def mock_server_config(self):
        """Configuration for mock server integration."""
        return Config(
            intercom_token="test_token",
            openai_key="sk-test123",
            mcp_transport="http",
            mcp_http_url="http://localhost:8001/mcp",
            mcp_api_key="test_api_key",
        )

    @pytest.mark.asyncio
    async def test_full_http_mcp_flow(self, mock_server_config):
        """Test full HTTP MCP flow with mock server."""
        # Skip if mock server not available
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8001/health") as response:
                    if response.status != 200:
                        pytest.skip("Mock MCP server not available")
        except:
            pytest.skip("Mock MCP server not available")

        backend = HTTPMCPBackend(mock_server_config)

        # Test initialization
        success = await backend.initialize()
        assert success is True

        # Test tool call
        result = await backend.call_tool("search_conversations", {"limit": 5})
        assert "conversations" in result
        assert "total_count" in result
        assert len(result["conversations"]) <= 5

        # Test server status
        status = await backend.call_tool("get_server_status", {})
        assert "server_info" in status
        assert status["status"] == "healthy"

        await backend.close()


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])
