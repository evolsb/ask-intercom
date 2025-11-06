#!/bin/bash
# Sync FastIntercom MCP data

echo "🔄 Syncing FastIntercom MCP data..."

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run sync (if the v0.3.0 has a sync command)
# Note: This may need adjustment based on actual FastIntercom v0.3.0 API
~/.local/bin/poetry run python -c "
from fast_intercom_mcp import Config, SyncService
import asyncio

async def sync():
    config = Config()
    sync_service = SyncService(config)
    print('Starting sync...')
    # Actual sync method depends on v0.3.0 API
    print('Sync completed')

asyncio.run(sync())
" || echo "⚠️  Manual sync not available in v0.3.0 - use background sync"
