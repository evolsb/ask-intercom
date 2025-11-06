"""Test fixtures for MCP testing."""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest

from src.config import Config
from src.mcp.http_mcp_backend import HTTPMCPBackend
from src.mcp.universal_adapter import LocalMCPBackend


@pytest.fixture
def mock_intercom_conversations():
    """Mock Intercom conversation data."""
    return [
        {
            "id": "conv_1",
            "created_at": "2025-06-23T10:00:00Z",
            "updated_at": "2025-06-23T10:30:00Z",
            "customer_email": "user1@example.com",
            "tags": ["support", "billing"],
            "messages": [
                {
                    "id": "msg_1_1",
                    "author_type": "user",
                    "body": "Hello, I have a billing question",
                    "created_at": "2025-06-23T10:00:00Z",
                },
                {
                    "id": "msg_1_2",
                    "author_type": "admin",
                    "body": "Hi! I'd be happy to help with your billing question.",
                    "created_at": "2025-06-23T10:15:00Z",
                },
            ],
        },
        {
            "id": "conv_2",
            "created_at": "2025-06-23T11:00:00Z",
            "updated_at": "2025-06-23T11:45:00Z",
            "customer_email": "user2@example.com",
            "tags": ["support", "technical"],
            "messages": [
                {
                    "id": "msg_2_1",
                    "author_type": "user",
                    "body": "I'm having trouble logging in",
                    "created_at": "2025-06-23T11:00:00Z",
                },
                {
                    "id": "msg_2_2",
                    "author_type": "admin",
                    "body": "Let me help you with that login issue.",
                    "created_at": "2025-06-23T11:10:00Z",
                },
            ],
        },
    ]


@pytest.fixture
def http_mcp_config():
    """HTTP MCP configuration for testing."""
    return Config(
        intercom_token="test_token_123",
        openai_key="sk-test123456",
        mcp_transport="http",
        mcp_http_url="http://localhost:8001/mcp",
        mcp_api_key="test_api_key",
    )


@pytest.fixture
def stdio_mcp_config():
    """Stdio MCP configuration for testing."""
    return Config(
        intercom_token="test_token_123",
        openai_key="sk-test123456",
        mcp_transport="stdio",
    )


@pytest.fixture
async def mock_http_backend(http_mcp_config):
    """Mock HTTP MCP backend for testing."""
    backend = HTTPMCPBackend(http_mcp_config)
    backend._initialized = True
    backend.http_session = AsyncMock()

    # Mock successful responses
    async def mock_call_tool(tool_name: str, params: dict):
        if tool_name == "get_server_status":
            return {
                "server_info": "Mock MCP Server",
                "status": "healthy",
                "conversation_count": 100,
            }
        elif tool_name == "search_conversations":
            return {
                "conversations": [
                    {"id": "conv_1", "messages": []},
                    {"id": "conv_2", "messages": []},
                ],
                "total_count": 2,
            }
        elif tool_name == "get_data_info":
            return {
                "status": "fresh",
                "has_data": True,
                "last_sync": "2025-06-23T10:00:00Z",
            }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    backend.call_tool = mock_call_tool
    return backend


@pytest.fixture
async def mock_local_backend(stdio_mcp_config):
    """Mock local MCP backend for testing."""
    backend = LocalMCPBackend(stdio_mcp_config.intercom_token)
    backend.server = AsyncMock()

    # Mock handle_request method
    async def mock_handle_request(request):
        tool_name = request["params"]["name"]

        if tool_name == "search_conversations":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"conversations": [{"id": "conv_1"}], "total_count": 1}',
                        }
                    ]
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -32601, "message": f"Method not found: {tool_name}"},
            }

    backend.server.handle_request = mock_handle_request
    await backend.initialize()
    return backend


class MockMCPServer:
    """Mock MCP server for testing."""

    def __init__(self, port: int = 8001):
        self.port = port
        self.process = None
        self.is_running = False

    async def start(self):
        """Start the mock MCP server."""
        try:
            # Import here to avoid circular imports
            import os
            import subprocess
            import sys

            # Start the mock server in background
            server_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "mock_mcp_server.py"
            )

            self.process = subprocess.Popen(
                [sys.executable, server_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait a moment for server to start
            await asyncio.sleep(2)

            # Check if server is responding
            import aiohttp

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{self.port}/health"
                    ) as response:
                        if response.status == 200:
                            self.is_running = True
                            return True
                except:
                    pass

            return False

        except Exception as e:
            print(f"Failed to start mock server: {e}")
            return False

    async def stop(self):
        """Stop the mock MCP server."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.is_running = False


@pytest.fixture
async def mock_mcp_server() -> AsyncGenerator[MockMCPServer, None]:
    """Fixture that provides a mock MCP server."""
    server = MockMCPServer()

    # Try to start the server
    started = await server.start()

    if started:
        yield server
    else:
        # If server couldn't start, yield None and tests should skip
        yield None

    # Cleanup
    await server.stop()


@pytest.fixture
def mcp_error_scenarios():
    """Common MCP error scenarios for testing."""
    return {
        "connection_timeout": {
            "error": "Connection timeout",
            "status_code": None,
            "exception": "asyncio.TimeoutError",
        },
        "auth_failure": {
            "error": "Authentication failed",
            "status_code": 401,
            "exception": None,
        },
        "server_unavailable": {
            "error": "Server unavailable",
            "status_code": 503,
            "exception": None,
        },
        "tool_not_found": {
            "error": "Tool not found",
            "status_code": 404,
            "exception": None,
        },
        "invalid_response": {
            "error": "Invalid JSON response",
            "status_code": 200,
            "exception": "json.JSONDecodeError",
        },
    }
