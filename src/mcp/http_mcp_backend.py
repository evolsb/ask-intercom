"""HTTP MCP Backend for external MCP servers."""

import json
from typing import Any, Dict, Optional

import aiohttp

from ..config import Config
from ..logger import get_logger

logger = get_logger("http_mcp_backend")


class HTTPMCPBackend:
    """MCP backend that connects to external MCP server via HTTP."""

    @property
    def backend_type(self) -> str:
        """Return backend type identifier."""
        return "http-mcp"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

        if self.config.mcp_transport != "http":
            raise ValueError("HTTPMCPBackend requires mcp_transport='http'")

    async def initialize(self) -> bool:
        """Initialize HTTP connection to external MCP server."""
        if self._initialized:
            return True

        logger.info(f"Initializing HTTP MCP backend to {self.config.mcp_http_url}")

        try:
            # Create HTTP session with auth headers
            headers = {
                "Authorization": f"Bearer {self.config.mcp_api_key}",
                "Content-Type": "application/json",
            }

            self.http_session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.mcp_timeout),
            )

            # Mark as initialized before testing connection
            self._initialized = True

            # Test connection with a simple ping/status request
            try:
                result = await self.call_tool("get_server_status", {})
                logger.info(
                    f"✅ Connected to HTTP MCP server: {result.get('server_info', 'Unknown')}"
                )
                return True
            except Exception as e:
                logger.error(f"❌ Failed to connect to HTTP MCP server: {e}")
                await self.close()
                return False

        except Exception as e:
            logger.error(f"Failed to initialize HTTP MCP backend: {e}")
            return False

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via HTTP."""
        if not self._initialized or not self.http_session:
            raise RuntimeError("Backend not initialized")

        # Construct HTTP endpoint for the tool
        url = f"{self.config.mcp_http_url.rstrip('/')}/tools/{tool_name}"

        logger.debug(f"Calling HTTP MCP tool: {tool_name} at {url}")

        try:
            async with self.http_session.post(url, json=params) as response:
                if response.status == 404:
                    raise ValueError(f"Tool '{tool_name}' not found on MCP server")
                elif response.status == 401:
                    raise RuntimeError(
                        "MCP server authentication failed - check MCP_API_KEY"
                    )
                elif response.status == 503:
                    raise RuntimeError(
                        "MCP server unavailable - check if server is running"
                    )
                elif response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"HTTP MCP error {response.status}: {error_text}"
                    )

                result = await response.json()
                logger.debug(f"HTTP MCP tool {tool_name} returned: {type(result)}")
                return result

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed for {tool_name}: {e}")
            raise RuntimeError(f"Failed to connect to MCP server: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from MCP server: {e}")
            raise RuntimeError(f"MCP server returned invalid response: {e}")

    async def close(self):
        """Close HTTP connection."""
        if self.http_session:
            try:
                await self.http_session.close()
                logger.info("HTTP MCP connection closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP connection: {e}")
            finally:
                self.http_session = None
                self._initialized = False
