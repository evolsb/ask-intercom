#!/bin/bash
# Simple FastIntercom MCP server startup using CLI

echo "🚀 Starting FastIntercom MCP Server (with auto-sync)..."

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for token
if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
    echo "❌ Error: INTERCOM_ACCESS_TOKEN not set"
    echo "Please set it in your .env file"
    exit 1
fi

# Initialize FastIntercom (if needed)
echo "🔧 Initializing FastIntercom MCP..."
~/.local/bin/poetry run python -m fast_intercom_mcp.cli init

# Start the server with auto-sync
echo "📡 Starting MCP server with built-in auto-sync..."
~/.local/bin/poetry run python -m fast_intercom_mcp.cli start
