#!/usr/bin/env python3
"""
Intercom MCP Server CLI

This CLI tool provides a working MCP implementation for Intercom that can be:
1. Used locally during development
2. Shared publicly as a standalone MCP server
3. Deployed as a service for teams

Usage:
    # Run as local MCP server (stdio)
    poetry run python -m src.mcp.cli --token YOUR_TOKEN

    # Run as HTTP server
    poetry run python -m src.mcp.cli --transport http --port 8080 --token YOUR_TOKEN

    # Use with Claude Desktop (add to settings)
    {
      "mcpServers": {
        "intercom": {
          "command": "poetry",
          "args": ["run", "python", "-m", "src.mcp.cli", "--token", "YOUR_TOKEN"],
          "cwd": "/path/to/ask-intercom-test"
        }
      }
    }
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from ..logger import get_logger
from .intercom_mcp_server import IntercomMCPServer, MCPServerRunner

logger = get_logger("mcp_cli")


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Intercom MCP Server - A working MCP implementation for Intercom",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run as local MCP server
    python -m src.mcp.cli --token dG9rOjgzMTEwOWRl...

    # Run as HTTP server
    python -m src.mcp.cli --transport http --port 8080

    # Use in Claude Desktop (add to ~/.claude/settings.json):
    {
      "mcpServers": {
        "intercom": {
          "command": "poetry",
          "args": ["run", "python", "-m", "src.mcp.cli"],
          "env": {"INTERCOM_ACCESS_TOKEN": "your_token_here"}
        }
      }
    }

Environment Variables:
    INTERCOM_ACCESS_TOKEN   Intercom API token (required if --token not provided)
    MCP_LOG_LEVEL          Log level (DEBUG, INFO, WARNING, ERROR)
        """,
    )

    # Transport options
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method (default: stdio for local use)",
    )

    parser.add_argument(
        "--host", default="localhost", help="HTTP host (default: localhost)"
    )

    parser.add_argument(
        "--port", type=int, default=8080, help="HTTP port (default: 8080)"
    )

    # Authentication
    parser.add_argument(
        "--token",
        default=os.getenv("INTERCOM_ACCESS_TOKEN"),
        help="Intercom access token (or set INTERCOM_ACCESS_TOKEN env var)",
    )

    # Configuration
    parser.add_argument("--config", type=Path, help="Path to configuration file (JSON)")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("MCP_LOG_LEVEL", "INFO"),
        help="Log level (default: INFO)",
    )

    # Utilities
    parser.add_argument(
        "--test", action="store_true", help="Test the server without starting it"
    )

    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Generate a sample configuration for Claude Desktop",
    )

    return parser


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)


def generate_claude_config(token: str = None) -> dict:
    """Generate Claude Desktop configuration."""
    cwd = os.getcwd()

    config = {
        "mcpServers": {
            "intercom": {
                "command": "poetry",
                "args": ["run", "python", "-m", "src.mcp.cli"],
                "cwd": cwd,
            }
        }
    }

    if token:
        config["mcpServers"]["intercom"]["env"] = {"INTERCOM_ACCESS_TOKEN": token}

    return config


async def test_server(token: str) -> bool:
    """Test server functionality."""
    logger.info("Testing Intercom MCP server...")

    try:
        # Create server instance
        server = IntercomMCPServer(token)

        # Test initialize
        init_response = await server.handle_initialize(
            "test-init",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"},
            },
        )

        if "error" in init_response:
            logger.error(f"Initialize failed: {init_response['error']}")
            return False

        logger.info("✅ Initialize request successful")

        # Test tools list
        tools_response = await server.handle_tools_list("test-tools", {})

        if "error" in tools_response:
            logger.error(f"Tools list failed: {tools_response['error']}")
            return False

        tools = tools_response["result"]["tools"]
        logger.info(f"✅ Tools list successful: {len(tools)} tools available")

        # Test a simple tool call
        search_response = await server.handle_tools_call(
            "test-search", {"name": "search_conversations", "arguments": {"limit": 1}}
        )

        if "error" in search_response:
            logger.error(f"Tool call failed: {search_response['error']}")
            return False

        logger.info("✅ Tool call successful")

        logger.info("🎉 All tests passed! Server is functional.")
        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set log level
    import logging

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Load config if provided
    config = {}
    if args.config:
        config = load_config(args.config)

        # Override CLI args with config
        for key, value in config.items():
            if hasattr(args, key) and value is not None:
                setattr(args, key, value)

    # Generate Claude Desktop config
    if args.generate_config:
        claude_config = generate_claude_config(args.token)
        print(json.dumps(claude_config, indent=2))

        config_path = Path.home() / ".claude" / "settings.json"
        print(f"\nTo use with Claude Desktop, add this to: {config_path}")
        return

    # Validate token
    if not args.token:
        logger.error(
            "Intercom access token required. Use --token or set INTERCOM_ACCESS_TOKEN"
        )
        sys.exit(1)

    # Test mode
    if args.test:
        success = await test_server(args.token)
        sys.exit(0 if success else 1)

    # Create and run server
    try:
        server = IntercomMCPServer(args.token)
        runner = MCPServerRunner(server)

        if args.transport == "stdio":
            logger.info("Starting Intercom MCP server on stdio")
            await runner.run_stdio()
        else:
            logger.info(
                f"Starting Intercom MCP server on http://{args.host}:{args.port}"
            )
            await runner.run_http(args.host, args.port)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
