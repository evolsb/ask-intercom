#!/bin/bash
# Start FastIntercom MCP Server

echo "🚀 Starting FastIntercom MCP Server..."

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

# Start the MCP server
echo "📡 Starting MCP server on stdio..."
exec ~/.local/bin/poetry run python -m fast_intercom_mcp.mcp_server
