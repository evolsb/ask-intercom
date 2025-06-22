"""Fixed MCP client with proper async request/response pattern."""

import asyncio
import json
import uuid
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from httpx_sse import aconnect_sse

from ..logger import get_logger

logger = get_logger("mcp_client")


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""

    pass


class MCPToolError(MCPError):
    """Raised when MCP tool call fails."""

    pass


class MCPConnection:
    """MCP connection with persistent SSE stream for async responses."""

    def __init__(self, server_url: str, auth_token: str, timeout: int = 30):
        self.server_url = server_url
        self.auth_token = auth_token
        self.timeout = timeout

        # Connection state
        self._connected = False
        self._session_endpoint: Optional[str] = None
        self._tools: List[str] = ["search_conversations", "get_conversation"]

        # OAuth token from mcp-remote
        self.oauth_token = self._load_mcp_oauth_token()

        # Async communication
        self._client: Optional[httpx.AsyncClient] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[str, Future] = {}
        self._running = False

    def _load_mcp_oauth_token(self) -> Optional[str]:
        """Load OAuth token from mcp-remote auth files."""
        mcp_auth_dir = Path.home() / ".mcp-auth"
        if not mcp_auth_dir.exists():
            logger.debug("No MCP auth directory found")
            return None

        for token_file in mcp_auth_dir.rglob("*_tokens.json"):
            try:
                with open(token_file) as f:
                    token_data = json.load(f)
                    access_token = token_data.get("access_token")
                    if access_token:
                        logger.info(f"Found MCP OAuth token from {token_file.name}")
                        return access_token
            except Exception as e:
                logger.warning(f"Failed to load token from {token_file}: {e}")

        logger.warning("No valid MCP OAuth tokens found")
        return None

    async def connect(self) -> bool:
        """Establish persistent MCP connection with SSE stream."""
        if self._connected:
            return True

        try:
            token_to_use = self.oauth_token if self.oauth_token else self.auth_token
            logger.info(f"Connecting to Intercom MCP server: {self.server_url}")

            headers = {
                "Authorization": f"Bearer {token_to_use}",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }

            # Create persistent HTTP client
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))

            # Establish SSE connection and get session endpoint
            session_endpoint = await self._get_session_endpoint(headers)
            if not session_endpoint:
                logger.error("Failed to get session endpoint")
                return False

            self._session_endpoint = session_endpoint
            logger.info(f"Session endpoint: {session_endpoint}")

            # Start persistent SSE listener for responses
            self._running = True
            self._sse_task = asyncio.create_task(self._sse_listener(headers))

            self._connected = True
            logger.info("MCP connection established successfully")
            return True

        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            await self._cleanup()
            return False

    async def _get_session_endpoint(self, headers: Dict[str, str]) -> Optional[str]:
        """Get session endpoint from initial SSE connection."""
        try:
            async with aconnect_sse(
                self._client, "GET", self.server_url, headers=headers
            ) as event_source:
                # Wait for endpoint event
                async for event in event_source.aiter_sse():
                    if event.event == "endpoint":
                        logger.debug(f"Received endpoint: {event.data}")
                        return event.data

                    # Don't wait too long
                    break

        except Exception as e:
            logger.error(f"Failed to get session endpoint: {e}")

        return None

    async def _sse_listener(self, headers: Dict[str, str]):
        """Persistent SSE listener for async responses."""
        logger.debug("Starting persistent SSE listener")

        retry_count = 0
        max_retries = 3

        while self._running and retry_count < max_retries:
            try:
                async with aconnect_sse(
                    self._client, "GET", self.server_url, headers=headers
                ) as event_source:
                    logger.debug("SSE connection established")
                    retry_count = 0  # Reset on successful connection

                    async for event in event_source.aiter_sse():
                        if not self._running:
                            break

                        await self._handle_sse_event(event)

            except Exception as e:
                retry_count += 1
                logger.warning(f"SSE connection lost (attempt {retry_count}): {e}")

                if self._running and retry_count < max_retries:
                    await asyncio.sleep(1 * retry_count)  # Backoff
                else:
                    break

        logger.debug("SSE listener stopped")

    async def _handle_sse_event(self, event):
        """Handle incoming SSE events."""
        logger.debug(
            f"SSE event: {event.event}, data: {event.data[:100] if event.data else 'None'}"
        )

        # Skip endpoint events (handled during connection)
        if event.event == "endpoint":
            return

        # Try to parse JSON-RPC response
        if event.data and event.data.strip():
            try:
                response_data = json.loads(event.data)
                request_id = response_data.get("id")

                if request_id and request_id in self._pending_requests:
                    # Complete the pending request
                    future = self._pending_requests.pop(request_id)
                    if not future.done():
                        future.set_result(response_data)
                        logger.debug(f"Completed request {request_id}")
                else:
                    logger.debug(f"Received unmatched response: {response_data}")

            except json.JSONDecodeError:
                logger.debug(f"Non-JSON SSE data: {event.data}")

    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send async request and wait for response via SSE."""
        if not self._connected or not self._session_endpoint:
            raise MCPConnectionError("Not connected to MCP server")

        request_id = payload.get("id")
        if not request_id:
            raise MCPError("Request payload must have 'id' field")

        try:
            # Set up future for response
            future = Future()
            self._pending_requests[request_id] = future

            # Send request
            token_to_use = self.oauth_token if self.oauth_token else self.auth_token
            headers = {
                "Authorization": f"Bearer {token_to_use}",
                "Content-Type": "application/json",
            }

            base_url = self.server_url.replace("/sse", "")
            full_url = f"{base_url}{self._session_endpoint}"

            logger.debug(f"Sending request {request_id} to {full_url}")

            response = await self._client.post(full_url, headers=headers, json=payload)

            if response.status_code != 202:
                self._pending_requests.pop(request_id, None)
                raise MCPError(
                    f"Request failed with status {response.status_code}: {response.text}"
                )

            logger.debug(f"Request {request_id} accepted, waiting for response...")

            # Wait for response via SSE
            try:
                result = await asyncio.wait_for(
                    asyncio.wrap_future(future), timeout=self.timeout
                )
                return result

            except asyncio.TimeoutError:
                self._pending_requests.pop(request_id, None)
                raise MCPError(f"Request {request_id} timed out after {self.timeout}s")

        except Exception as e:
            self._pending_requests.pop(request_id, None)
            logger.error(f"Request {request_id} failed: {e}")
            raise MCPError(f"Request failed: {e}") from e

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return results."""
        if not self._connected:
            raise MCPConnectionError("Not connected to MCP server")

        try:
            request_payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": params},
            }

            logger.debug(f"Calling MCP tool: {tool_name} with params: {params}")

            response = await self._send_request(request_payload)

            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                raise MCPToolError(f"Tool '{tool_name}' failed: {error_msg}")

            result = response.get("result", {})
            logger.debug(f"MCP tool '{tool_name}' returned: {len(str(result))} chars")

            return result

        except MCPToolError:
            raise
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            raise MCPToolError(f"Failed to call tool '{tool_name}': {e}") from e

    async def search_conversations(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search conversations using MCP."""
        return await self.call_tool("search_conversations", filters)

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation details using MCP."""
        return await self.call_tool(
            "get_conversation", {"conversation_id": conversation_id}
        )

    async def disconnect(self):
        """Clean disconnect from MCP server."""
        await self._cleanup()

    async def _cleanup(self):
        """Clean up resources."""
        logger.debug("Cleaning up MCP connection")

        self._running = False
        self._connected = False

        # Cancel SSE listener
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

        # Fail pending requests
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.set_exception(
                    MCPError(f"Connection closed while waiting for {request_id}")
                )
        self._pending_requests.clear()

        # Close HTTP client
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Factory function for easier usage
async def create_mcp_connection(
    server_url: str, auth_token: str, timeout: int = 30
) -> MCPConnection:
    """Create and connect an MCP connection."""
    connection = MCPConnection(server_url, auth_token, timeout)
    await connection.connect()
    return connection
