"""
Intercom MCP Server - A working MCP implementation wrapping Intercom's REST API.

This server implements the Model Context Protocol specification to provide
standardized access to Intercom data. It can be used as:
1. A drop-in replacement for Intercom's broken MCP implementation
2. A local MCP server for development
3. A public MCP server that others can use

Architecture:
- Implements standard MCP protocol over stdio/HTTP
- Wraps Intercom REST API with proper error handling
- Provides tools: search_conversations, get_conversation, list_contacts
- Supports streaming responses for large datasets
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Dict, List

import httpx

from ..logger import get_logger

logger = get_logger("intercom_mcp_server")


class IntercomMCPServer:
    """MCP Server implementation for Intercom."""

    def __init__(self, intercom_token: str):
        self.intercom_token = intercom_token
        self.base_url = "https://api.intercom.io"
        self.server_info = {
            "name": "intercom-mcp-server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
        }
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available MCP tools."""
        return [
            {
                "name": "search_conversations",
                "description": "Search Intercom conversations with filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (optional)",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "snoozed", "all"],
                            "description": "Conversation state filter",
                        },
                        "created_after": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Filter conversations created after this date",
                        },
                        "created_before": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Filter conversations created before this date",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 150,
                            "default": 50,
                            "description": "Maximum number of conversations to return",
                        },
                    },
                },
            },
            {
                "name": "get_conversation",
                "description": "Get a specific Intercom conversation by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "The conversation ID",
                        },
                        "include_parts": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include conversation parts (messages)",
                        },
                    },
                    "required": ["conversation_id"],
                },
            },
            {
                "name": "list_contacts",
                "description": "List Intercom contacts with optional filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Filter by email address",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 150,
                            "default": 50,
                            "description": "Maximum number of contacts to return",
                        },
                    },
                },
            },
        ]

    async def handle_initialize(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": self.server_info["protocolVersion"],
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": False},
                    "prompts": {},
                },
                "serverInfo": self.server_info,
            },
        }

    async def handle_tools_list(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tools}}

    async def handle_tools_call(
        self, request_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.debug(f"Calling tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "search_conversations":
                result = await self._search_conversations(arguments)
            elif tool_name == "get_conversation":
                result = await self._get_conversation(arguments)
            elif tool_name == "list_contacts":
                result = await self._list_contacts(arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                },
            }

        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}",
                },
            }

    async def _search_conversations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search conversations using Intercom REST API."""
        headers = {
            "Authorization": f"Bearer {self.intercom_token}",
            "Accept": "application/json",
            "Intercom-Version": "2.11",
        }

        # Build query parameters
        query_params = {"per_page": params.get("limit", 50), "order": "desc"}

        if "state" in params and params["state"] != "all":
            query_params["state"] = params["state"]

        if "created_after" in params:
            # Convert to Unix timestamp
            dt = datetime.fromisoformat(params["created_after"].replace("Z", "+00:00"))
            query_params["created_at_after"] = int(dt.timestamp())

        if "created_before" in params:
            dt = datetime.fromisoformat(params["created_before"].replace("Z", "+00:00"))
            query_params["created_at_before"] = int(dt.timestamp())

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/conversations", headers=headers, params=query_params
            )

            response.raise_for_status()
            data = response.json()

            # Format response
            return {
                "conversations": data.get("conversations", []),
                "total_count": data.get("total_count", 0),
                "has_more": data.get("pages", {}).get("next") is not None,
            }

    async def _get_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific conversation."""
        conversation_id = params["conversation_id"]
        include_parts = params.get("include_parts", True)

        headers = {
            "Authorization": f"Bearer {self.intercom_token}",
            "Accept": "application/json",
            "Intercom-Version": "2.11",
        }

        async with httpx.AsyncClient() as client:
            # Get conversation
            response = await client.get(
                f"{self.base_url}/conversations/{conversation_id}", headers=headers
            )

            response.raise_for_status()
            conversation = response.json()

            # Get conversation parts if requested
            if include_parts:
                parts_response = await client.get(
                    f"{self.base_url}/conversations/{conversation_id}/parts",
                    headers=headers,
                )

                if parts_response.status_code == 200:
                    parts_data = parts_response.json()
                    conversation["parts"] = parts_data.get("conversation_parts", [])

            return conversation

    async def _list_contacts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List contacts."""
        headers = {
            "Authorization": f"Bearer {self.intercom_token}",
            "Accept": "application/json",
            "Intercom-Version": "2.11",
        }

        query_params = {"per_page": params.get("limit", 50)}

        if "email" in params:
            query_params["email"] = params["email"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/contacts", headers=headers, params=query_params
            )

            response.raise_for_status()
            data = response.json()

            return {
                "contacts": data.get("data", []),
                "total_count": data.get("total_count", 0),
                "has_more": data.get("pages", {}).get("next") is not None,
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request."""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        logger.debug(f"Handling request: {method}")

        if method == "initialize":
            return await self.handle_initialize(request_id, params)
        elif method == "tools/list":
            return await self.handle_tools_list(request_id, params)
        elif method == "tools/call":
            return await self.handle_tools_call(request_id, params)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }


class MCPServerRunner:
    """Runs the MCP server with different transports."""

    def __init__(self, server: IntercomMCPServer):
        self.server = server

    async def run_stdio(self):
        """Run MCP server over stdio (for local usage)."""
        logger.info("Starting Intercom MCP server on stdio")

        # Read from stdin, write to stdout
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                # Read line from stdin
                line = await reader.readline()
                if not line:
                    break

                # Parse JSON-RPC request
                request = json.loads(line.decode())

                # Handle request
                response = await self.server.handle_request(request)

                # Write response to stdout
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                logger.error(f"Error handling request: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    async def run_http(self, host: str = "localhost", port: int = 8080):
        """Run MCP server over HTTP (for remote usage)."""
        from aiohttp import web

        async def handle_mcp(request: web.Request) -> web.Response:
            """Handle HTTP MCP requests."""
            try:
                # Parse JSON-RPC request
                data = await request.json()

                # Handle request
                response = await self.server.handle_request(data)

                return web.json_response(response)

            except Exception as e:
                logger.error(f"HTTP request failed: {e}")
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": str(e)},
                    },
                    status=400,
                )

        # Create web app
        app = web.Application()
        app.router.add_post("/", handle_mcp)

        logger.info(f"Starting Intercom MCP server on http://{host}:{port}")

        # Run server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        # Keep running
        await asyncio.Event().wait()


# CLI entry point
async def main():
    """Run the Intercom MCP server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Intercom MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method (default: stdio)",
    )
    parser.add_argument(
        "--host", default="localhost", help="HTTP host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="HTTP port (default: 8080)"
    )
    parser.add_argument(
        "--token",
        default=os.getenv("INTERCOM_ACCESS_TOKEN"),
        help="Intercom access token (or set INTERCOM_ACCESS_TOKEN env var)",
    )

    args = parser.parse_args()

    if not args.token:
        print("Error: Intercom access token required", file=sys.stderr)
        sys.exit(1)

    # Create server
    server = IntercomMCPServer(args.token)
    runner = MCPServerRunner(server)

    # Run with selected transport
    if args.transport == "stdio":
        await runner.run_stdio()
    else:
        await runner.run_http(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())
