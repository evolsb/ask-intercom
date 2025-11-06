#!/bin/bash
# Start FastIntercom MCP with auto-sync daemon

echo "🚀 Starting FastIntercom MCP with Auto-Sync Daemon..."

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

# Create log directory
mkdir -p .ask-intercom-analytics/logs

# Start the MCP server with background sync enabled
echo "📡 Starting MCP server with auto-sync on stdio..."
~/.local/bin/poetry run python -c "
import asyncio
import os
from fast_intercom_mcp.mcp_server import FastIntercomMCPServer
from fast_intercom_mcp.database import DatabaseManager
from fast_intercom_mcp.sync_service import SyncService

async def run_with_auto_sync():
    # Initialize components
    db_manager = DatabaseManager()
    sync_service = SyncService()
    
    # Create server
    server = FastIntercomMCPServer(
        database_manager=db_manager,
        sync_service=sync_service
    )
    
    # Start background sync
    await server.start_background_sync()
    print('Background sync started', flush=True)
    
    # Run the MCP server
    await server.run()

asyncio.run(run_with_auto_sync())
"
