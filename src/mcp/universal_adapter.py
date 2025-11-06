"""
Universal MCP Adapter - MCP-only interface for multi-backend support.

This adapter provides a unified MCP interface that can use:
1. FastIntercomMCP (preferred, high-performance caching)
2. Official Intercom MCP (dormant until functional)
3. Local MCP-REST wrapper (fallback for non-FastIntercomMCP users)

The adapter automatically detects which MCP backend works and uses it.
ALL backends speak MCP protocol - no mixed protocol handling.
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..logger import get_logger
from ..models import Conversation, ConversationFilters, Message
from .client import MCPConnection
from .http_mcp_backend import HTTPMCPBackend
from .intercom_mcp_server import IntercomMCPServer

logger = get_logger("universal_mcp_adapter")


class MCPBackend(ABC):
    """Abstract base for MCP backends."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the backend."""
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return backend type identifier."""
        pass


class OfficialMCPBackend(MCPBackend):
    """Backend using official Intercom MCP."""

    def __init__(self, server_url: str, auth_token: str):
        self.connection = MCPConnection(server_url, auth_token)

    async def initialize(self) -> bool:
        """Test if official MCP is working."""
        try:
            # Try to connect
            connected = await self.connection.connect()
            if not connected:
                return False

            # Try a simple tool call with short timeout
            await asyncio.wait_for(
                self.connection.call_tool("tools/list", {}), timeout=5.0
            )

            # If we get here, it's working!
            logger.info("Official Intercom MCP is functional!")
            return True

        except asyncio.TimeoutError:
            logger.debug("Official MCP timed out (expected)")
            return False
        except Exception as e:
            logger.debug(f"Official MCP failed: {e}")
            return False

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via official MCP."""
        return await self.connection.call_tool(tool_name, params)

    async def close(self):
        """Disconnect from MCP."""
        await self.connection.disconnect()

    @property
    def backend_type(self) -> str:
        return "official_mcp"


class LocalMCPBackend(MCPBackend):
    """Backend using our local MCP server."""

    def __init__(self, intercom_token: str):
        self.intercom_token = intercom_token
        self.server_process: Optional[subprocess.Popen] = None
        self.server = IntercomMCPServer(intercom_token)

    async def initialize(self) -> bool:
        """Start local MCP server."""
        try:
            # For in-process usage, we can directly use the server
            logger.info("Initializing local MCP server backend")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize local MCP: {e}")
            return False

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via local MCP server."""
        # Create a tools/call request
        request = {
            "jsonrpc": "2.0",
            "id": f"local-{tool_name}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": params},
        }

        # Handle request directly
        response = await self.server.handle_request(request)

        if "error" in response:
            raise Exception(response["error"]["message"])

        # Extract result
        result = response.get("result", {})
        content = result.get("content", [])

        if content and content[0]["type"] == "text":
            return json.loads(content[0]["text"])

        return {}

    async def close(self):
        """Stop local MCP server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()

    @property
    def backend_type(self) -> str:
        return "local_mcp"


class UniversalMCPAdapter:
    """
    Universal MCP-only adapter that selects the best available MCP backend.

    Priority order:
    1. FastIntercomMCP (preferred, high-performance caching)
    2. Official Intercom MCP (dormant until functional)
    3. Local MCP-REST wrapper (fallback)

    ALL backends implement MCP protocol for consistent interface.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        intercom_token: Optional[str] = None,
        mcp_server_url: str = "https://mcp.intercom.com/sse",
        force_backend: Optional[str] = None,
    ):
        self.config = config or Config.from_env()
        self.intercom_token = intercom_token or self.config.intercom_token
        self.mcp_server_url = mcp_server_url
        self.force_backend = force_backend
        self.backend: Optional[MCPBackend] = None
        self.available_backends: Dict[str, MCPBackend] = {}
        self.last_sync_info: Optional[Dict] = None

    async def initialize(self):
        """Initialize and select the best backend."""
        logger.info("Initializing Universal MCP Adapter")

        # If backend is forced, use it
        if self.force_backend:
            logger.info(f"Forcing backend: {self.force_backend}")
            if self.force_backend == "official_mcp":
                raise ValueError(
                    "Official MCP backend is dormant and not available for use"
                )
            elif self.force_backend == "http_mcp":
                self.backend = HTTPMCPBackend(self.config)
            elif self.force_backend == "local_mcp":
                self.backend = LocalMCPBackend(self.intercom_token)
            else:
                raise ValueError(f"Unknown backend: {self.force_backend}")

            if await self.backend.initialize():
                logger.info(
                    f"Forced backend {self.force_backend} initialized successfully"
                )
                return
            else:
                raise Exception(
                    f"Forced backend {self.force_backend} failed to initialize"
                )

        # Test MCP backends in priority order
        backends_to_test = []

        # Choose backend based on transport configuration
        if self.config.mcp_transport == "http":
            # Use HTTP MCP backend for external servers
            backends_to_test.append(("http_mcp", HTTPMCPBackend(self.config)))
        else:
            # Use local MCP wrapper for stdio transport
            backends_to_test.append(("local_mcp", LocalMCPBackend(self.intercom_token)))

        # Test each backend
        for backend_name, backend_instance in backends_to_test:
            logger.debug(f"Testing backend: {backend_name}")

            try:
                if await backend_instance.initialize():
                    logger.info(f"✅ Backend {backend_name} is functional")
                    self.available_backends[backend_name] = backend_instance

                    # Use first working backend
                    if not self.backend:
                        self.backend = backend_instance
                        logger.info(f"Selected backend: {backend_name}")
                else:
                    logger.debug(f"❌ Backend {backend_name} failed initialization")

            except Exception as e:
                logger.debug(f"❌ Backend {backend_name} error: {e}")

        if not self.backend:
            raise Exception("No functional backend available")

        # Log available backends
        logger.info(f"Available backends: {list(self.available_backends.keys())}")
        logger.info(f"Using backend: {self.backend.backend_type}")

    async def search_conversations(
        self, filters: ConversationFilters
    ) -> List[Conversation]:
        """Search conversations using selected backend."""
        if not self.backend:
            raise Exception("Adapter not initialized")

        # Convert filters to params
        params = {"limit": filters.limit or 50}

        if filters.start_date:
            params["created_after"] = filters.start_date.isoformat()

        if filters.end_date:
            params["created_before"] = filters.end_date.isoformat()

        # Call backend
        result = await self.backend.call_tool("search_conversations", params)

        # Handle sync info if present (from FastIntercomMCP backend)
        if "sync_info" in result:
            sync_info = result["sync_info"]
            sync_state = sync_info.get("state")

            if sync_state == "partial" and sync_info.get("message"):
                logger.warning(f"Data freshness warning: {sync_info['message']}")
            elif sync_state == "stale":
                logger.warning(f"Data may be stale: {sync_info['message']}")
            elif sync_state == "fresh":
                logger.info("Using fresh cached data")

            # Store sync info for potential future use
            self.last_sync_info = sync_info
        else:
            self.last_sync_info = None

        # Convert to Conversation objects
        conversations = []
        for conv_data in result.get("conversations", []):
            # Convert messages
            messages = []
            for msg_data in conv_data.get("messages", []):
                messages.append(
                    Message(
                        id=msg_data["id"],
                        author_type=msg_data["author_type"],
                        body=msg_data["body"],
                        created_at=datetime.fromisoformat(
                            msg_data["created_at"].replace("Z", "+00:00")
                        ),
                    )
                )

            # Create conversation
            conversations.append(
                Conversation(
                    id=conv_data["id"],
                    created_at=datetime.fromisoformat(
                        conv_data["created_at"].replace("Z", "+00:00")
                    ),
                    messages=messages,
                    customer_email=conv_data.get("customer_email"),
                    tags=conv_data.get("tags", []),
                )
            )

        return conversations

    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get a specific conversation."""
        if not self.backend:
            raise Exception("Adapter not initialized")

        result = await self.backend.call_tool(
            "get_conversation", {"conversation_id": conversation_id}
        )

        # Convert messages
        messages = []
        for msg_data in result.get("messages", []):
            messages.append(
                Message(
                    id=msg_data["id"],
                    author_type=msg_data["author_type"],
                    body=msg_data["body"],
                    created_at=datetime.fromisoformat(
                        msg_data["created_at"].replace("Z", "+00:00")
                    ),
                )
            )

        # Create conversation
        return Conversation(
            id=result["id"],
            created_at=datetime.fromisoformat(
                result["created_at"].replace("Z", "+00:00")
            ),
            messages=messages,
            customer_email=result.get("customer_email"),
            tags=result.get("tags", []),
        )

    async def switch_backend(self, backend_name: str):
        """Switch to a different backend if available."""
        if backend_name not in self.available_backends:
            raise ValueError(f"Backend {backend_name} not available")

        logger.info(f"Switching from {self.backend.backend_type} to {backend_name}")

        # Close current backend
        if self.backend:
            await self.backend.close()

        # Switch to new backend
        self.backend = self.available_backends[backend_name]

    async def close(self):
        """Clean up all backends."""
        for backend in self.available_backends.values():
            try:
                await backend.close()
            except Exception as e:
                logger.error(f"Error closing backend: {e}")

    @property
    def current_backend(self) -> str:
        """Get current backend type."""
        return self.backend.backend_type if self.backend else "none"

    @property
    def is_using_mcp(self) -> bool:
        """Check if using any MCP implementation (always True in MCP-only architecture)."""
        return True


# Factory function for easy usage
async def create_universal_adapter(
    intercom_token: Optional[str] = None,
    config: Optional[Config] = None,
    force_backend: Optional[str] = None,
) -> UniversalMCPAdapter:
    """Create and initialize a universal adapter."""
    adapter = UniversalMCPAdapter(
        config=config,
        intercom_token=intercom_token,
        force_backend=force_backend,
    )
    await adapter.initialize()
    return adapter
