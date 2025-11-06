# FastIntercom MCP Update Instructions for AI Dev Agent

## Overview
FastIntercom MCP needs to implement metadata tools to support stateless freshness checking and add background sync capabilities. The MCP server should be a single process with:
- Stateless MCP interface layer (tools)
- Internal background sync process (runs every 15 minutes)
- SQLite database for fast conversation access

This allows ask-intercom to determine if cached data is fresh enough while maintaining proper MCP compliance.

## Architecture Overview

```
┌─────────────────────────────────────┐
│      FastIntercom MCP Server       │
│           (Single Process)          │
│                                     │
│  ┌─────────────────┐               │
│  │ MCP Interface   │◄──── Clients  │
│  │ (Stateless)     │               │
│  └─────────┬───────┘               │
│            │                       │
│  ┌─────────▼───────┐               │
│  │ SQLite Database │               │
│  │ + Metadata      │               │
│  └─────────▲───────┘               │
│            │                       │
│  ┌─────────┴───────┐               │
│  │ Background Sync │               │
│  │ (Every 15 min)  │               │
│  └─────────────────┘               │
└─────────────────────────────────────┘
```

## Required Changes

### 1. Add Metadata Table to SQLite Database

Create a new table to track sync metadata:

```sql
-- In the database initialization code, add:
CREATE TABLE IF NOT EXISTS sync_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_started_at TIMESTAMP NOT NULL,
    sync_completed_at TIMESTAMP,
    sync_status TEXT NOT NULL, -- 'in_progress', 'completed', 'failed'
    coverage_start_date DATE,
    coverage_end_date DATE,
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    sync_type TEXT, -- 'full', 'incremental'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookups
CREATE INDEX idx_sync_metadata_completed ON sync_metadata(sync_completed_at DESC);
```

### 2. Add Background Sync Service

Create a background sync service that runs inside the MCP server process:

```python
# In a new file: background_sync.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class BackgroundSyncService:
    """Background sync service that runs inside the MCP server process."""
    
    def __init__(self, db_manager, intercom_client, sync_interval_minutes: int = 15):
        self.db = db_manager
        self.intercom_client = intercom_client
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.running = False
        self.sync_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background sync service."""
        if self.running:
            return
        
        self.running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Background sync started with {self.sync_interval.total_seconds()/60} minute interval")
    
    async def stop(self):
        """Stop the background sync service."""
        self.running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Background sync stopped")
    
    async def _sync_loop(self):
        """Main sync loop - runs continuously."""
        # Initial sync on startup
        await self._perform_sync()
        
        while self.running:
            try:
                await asyncio.sleep(self.sync_interval.total_seconds())
                if self.running:  # Check again after sleep
                    await self._perform_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                # Continue running, retry in next interval
    
    async def _perform_sync(self):
        """Perform a single sync operation with metadata tracking."""
        start_time = datetime.now()
        
        # Default to syncing last 7 days
        end_date = start_time
        start_date = end_date - timedelta(days=7)
        
        # Start sync - write metadata
        sync_id = await self.db.execute("""
            INSERT INTO sync_metadata 
            (sync_started_at, sync_status, sync_type, coverage_start_date, coverage_end_date)
            VALUES (?, 'in_progress', 'background', ?, ?)
        """, [start_time, start_date.date(), end_date.date()])
        
        try:
            logger.info(f"Starting background sync for {start_date.date()} to {end_date.date()}")
            
            # Fetch conversations from Intercom
            conversations = await self.intercom_client.fetch_conversations(
                start_date=start_date,
                end_date=end_date
            )
            
            # Store conversations in database
            await self.db.store_conversations(conversations)
            
            total_convos = len(conversations)
            total_msgs = sum(len(c.messages) for c in conversations)
            
            # Update metadata on success
            await self.db.execute("""
                UPDATE sync_metadata 
                SET sync_completed_at = ?,
                    sync_status = 'completed',
                    total_conversations = ?,
                    total_messages = ?
                WHERE id = ?
            """, [datetime.now(), total_convos, total_msgs, sync_id])
            
            logger.info(f"Background sync completed: {total_convos} conversations, {total_msgs} messages")
            
        except Exception as e:
            logger.error(f"Background sync failed: {e}")
            
            # Update metadata on failure
            await self.db.execute("""
                UPDATE sync_metadata 
                SET sync_completed_at = ?,
                    sync_status = 'failed',
                    error_message = ?
                WHERE id = ?
            """, [datetime.now(), str(e), sync_id])
    
    async def force_sync(self) -> bool:
        """Force an immediate sync (callable from MCP tools)."""
        try:
            await self._perform_sync()
            return True
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            return False
```

### 3. Add New MCP Tools

In `mcp_server.py`, add these tool definitions:

```python
@server.tool()
async def get_data_info() -> Dict[str, Any]:
    """
    Get information about cached data freshness and coverage.
    This is a stateless read operation.
    """
    try:
        # Query the most recent successful sync
        result = await db.fetchone("""
            SELECT 
                sync_completed_at,
                coverage_start_date,
                coverage_end_date,
                total_conversations,
                total_messages,
                sync_type
            FROM sync_metadata
            WHERE sync_status = 'completed'
            ORDER BY sync_completed_at DESC
            LIMIT 1
        """)
        
        if not result:
            return {
                "has_data": False,
                "message": "No successful sync found"
            }
        
        last_sync = result['sync_completed_at']
        data_age_minutes = int((datetime.now() - last_sync).total_seconds() / 60)
        
        # Also get database size
        db_path = Path(db.path)
        db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)
        
        return {
            "has_data": True,
            "last_sync": last_sync.isoformat(),
            "data_age_minutes": data_age_minutes,
            "coverage_start": result['coverage_start_date'].isoformat(),
            "coverage_end": result['coverage_end_date'].isoformat(),
            "total_conversations": result['total_conversations'],
            "total_messages": result['total_messages'],
            "sync_type": result['sync_type'],
            "database_size_mb": db_size_mb
        }
        
    except Exception as e:
        logger.error(f"Error getting data info: {e}")
        return {
            "has_data": False,
            "error": str(e)
        }


@server.tool()
async def check_coverage(
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Check if cached data covers the requested date range.
    
    Args:
        start_date: ISO format date string
        end_date: ISO format date string
    
    Returns:
        Dict with coverage information
    """
    try:
        query_start = datetime.fromisoformat(start_date).date()
        query_end = datetime.fromisoformat(end_date).date()
        
        # Get the most recent sync info
        result = await db.fetchone("""
            SELECT 
                sync_completed_at,
                coverage_start_date,
                coverage_end_date
            FROM sync_metadata
            WHERE sync_status = 'completed'
            ORDER BY sync_completed_at DESC
            LIMIT 1
        """)
        
        if not result:
            return {
                "has_coverage": False,
                "reason": "No data available",
                "coverage_gaps": [(start_date, end_date)]
            }
        
        coverage_start = result['coverage_start_date']
        coverage_end = result['coverage_end_date']
        data_age_minutes = int((datetime.now() - result['sync_completed_at']).total_seconds() / 60)
        
        # Check if query range is within coverage
        has_full_coverage = (query_start >= coverage_start and query_end <= coverage_end)
        
        # Calculate gaps if any
        coverage_gaps = []
        if query_start < coverage_start:
            coverage_gaps.append((query_start.isoformat(), coverage_start.isoformat()))
        if query_end > coverage_end:
            coverage_gaps.append((coverage_end.isoformat(), query_end.isoformat()))
        
        return {
            "has_coverage": has_full_coverage,
            "partial_coverage": len(coverage_gaps) > 0 and query_start <= coverage_end and query_end >= coverage_start,
            "coverage_gaps": coverage_gaps,
            "cached_range": {
                "start": coverage_start.isoformat(),
                "end": coverage_end.isoformat()
            },
            "data_age_minutes": data_age_minutes,
            "reason": "Full coverage" if has_full_coverage else f"Missing data for {len(coverage_gaps)} date ranges"
        }
        
    except Exception as e:
        logger.error(f"Error checking coverage: {e}")
        return {
            "has_coverage": False,
            "error": str(e)
        }
```

### 4. Update Tool Definitions

Add the new tools to the server's tool list:

```python
# In the server initialization or tool registration
tools = [
    {
        "name": "get_data_info",
        "description": "Get information about cached data freshness and coverage",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "check_coverage", 
        "description": "Check if cached data covers a specific date range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DD or full ISO timestamp)"
                },
                "end_date": {
                    "type": "string", 
                    "description": "End date in ISO format (YYYY-MM-DD or full ISO timestamp)"
                }
            },
            "required": ["start_date", "end_date"]
        }
    },
    # ... existing tools like search_conversations, etc.
]
```

### 5. Update Sync Command to Handle Different Time Ranges

In the CLI sync command:

```python
@click.command()
@click.option('--days', default=7, help='Number of days to sync')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--full', is_flag=True, help='Full sync (last 90 days)')
async def sync(days, start_date, end_date, full):
    """Sync Intercom conversations to local cache."""
    
    # Determine date range
    if full:
        end = datetime.now()
        start = end - timedelta(days=90)
        sync_type = 'full'
    elif start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        sync_type = 'incremental'
    else:
        end = datetime.now()
        start = end - timedelta(days=days)
        sync_type = 'incremental'
    
    # Track in metadata
    await db.execute("""
        INSERT INTO sync_metadata 
        (sync_started_at, sync_status, sync_type, coverage_start_date, coverage_end_date)
        VALUES (?, 'in_progress', ?, ?, ?)
    """, [datetime.now(), sync_type, start.date(), end.date()])
    
    # ... rest of sync logic
```

### 6. Update Main MCP Server to Include Background Sync

Modify the main MCP server to include the background sync service:

```python
# In mcp_server.py or main server file
import asyncio
from mcp.server import Server
from .background_sync import BackgroundSyncService

class FastIntercomMCPServer:
    """Main MCP server with background sync capabilities."""
    
    def __init__(self):
        self.server = Server("fastintercom")
        self.db = DatabaseManager()
        self.intercom_client = IntercomClient()
        self.background_sync = BackgroundSyncService(
            db_manager=self.db,
            intercom_client=self.intercom_client,
            sync_interval_minutes=15  # Configurable
        )
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        # Existing tools
        @self.server.tool()
        async def search_conversations(**params):
            """Search cached conversations."""
            return await self.db.search_conversations(params)
        
        # New metadata tools
        @self.server.tool()
        async def get_data_info():
            """Get information about cached data freshness and coverage."""
            # ... (same implementation as before)
        
        @self.server.tool()
        async def check_coverage(start_date: str, end_date: str):
            """Check if cached data covers the requested date range."""
            # ... (same implementation as before)
        
        # New sync control tools
        @self.server.tool()
        async def get_sync_status():
            """Check if a sync is currently in progress."""
            try:
                # Check for in-progress syncs
                in_progress = await self.db.fetchone("""
                    SELECT sync_started_at, coverage_start_date, coverage_end_date
                    FROM sync_metadata
                    WHERE sync_status = 'in_progress'
                    ORDER BY sync_started_at DESC
                    LIMIT 1
                """)
                
                if in_progress:
                    duration_minutes = int((datetime.now() - in_progress['sync_started_at']).total_seconds() / 60)
                    return {
                        "is_syncing": True,
                        "sync_started_at": in_progress['sync_started_at'].isoformat(),
                        "duration_minutes": duration_minutes,
                        "coverage_dates": {
                            "start": in_progress['coverage_start_date'].isoformat(),
                            "end": in_progress['coverage_end_date'].isoformat()
                        }
                    }
                
                return {
                    "is_syncing": False
                }
                
            except Exception as e:
                return {
                    "is_syncing": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def force_sync():
            """Force an immediate sync operation."""
            try:
                success = await self.background_sync.force_sync()
                return {
                    "success": success,
                    "message": "Sync completed successfully" if success else "Sync failed"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
    
    async def start(self):
        """Start the MCP server and background sync."""
        # Start background sync
        await self.background_sync.start()
        
        # Start MCP server
        await self.server.start()
    
    async def stop(self):
        """Stop the MCP server and background sync."""
        await self.background_sync.stop()
        await self.server.stop()

# Main entry point
async def main():
    server = FastIntercomMCPServer()
    
    try:
        await server.start()
        # Keep running until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Testing Instructions

1. **Test MCP server startup:**
   ```bash
   # Start the MCP server (should begin background sync automatically)
   python -m fastintercom.mcp_server
   
   # Check logs for background sync startup messages
   ```

2. **Test metadata table creation:**
   ```bash
   # Verify table exists after server starts
   sqlite3 ~/.fastintercom/data.db ".schema sync_metadata"
   ```

3. **Test MCP tools:**
   ```bash
   # Use mcp-client or ask-intercom to test new tools
   mcp-client call get_data_info
   mcp-client call check_coverage --start-date "2024-06-20" --end-date "2024-06-22"
   mcp-client call get_sync_status
   mcp-client call force_sync
   ```

4. **Test background sync behavior:**
   ```bash
   # Check that sync metadata is being written every 15 minutes
   sqlite3 ~/.fastintercom/data.db "SELECT * FROM sync_metadata ORDER BY id DESC LIMIT 5"
   
   # Verify conversations are being updated
   sqlite3 ~/.fastintercom/data.db "SELECT COUNT(*) FROM conversations"
   ```

## Expected Behavior

After these changes:

1. **MCP server starts** and immediately begins background sync
2. **Background sync runs every 15 minutes** keeping data fresh
3. **MCP tools provide metadata** about data freshness and coverage
4. **Clients can query freshness** via MCP protocol (no filesystem access)
5. **Manual sync control** available via `force_sync` tool
6. **Graceful shutdown** stops both MCP server and background sync

## Configuration Options

Add these to the MCP server configuration:

```python
# Environment variables or config file
FASTINTERCOM_SYNC_INTERVAL_MINUTES=15  # How often to sync
FASTINTERCOM_SYNC_DAYS=7               # How many days to sync each time
FASTINTERCOM_DB_PATH=~/.fastintercom/data.db  # Database location
INTERCOM_ACCESS_TOKEN=your_token_here  # Required for sync
```

## Migration for Existing Databases

```sql
-- For existing FastIntercom installations, run this migration:
-- Check if table exists first
SELECT name FROM sqlite_master WHERE type='table' AND name='sync_metadata';

-- If not, create it and populate with initial data
INSERT INTO sync_metadata (
    sync_started_at,
    sync_completed_at, 
    sync_status,
    coverage_start_date,
    coverage_end_date,
    total_conversations,
    sync_type
)
SELECT 
    datetime('now', '-1 hour'),
    datetime('now'),
    'completed',
    date('now', '-7 days'),
    date('now'),
    (SELECT COUNT(*) FROM conversations),
    'migration'
WHERE NOT EXISTS (SELECT 1 FROM sync_metadata);
```

## Key Benefits

1. **Single Process**: Everything runs in one FastIntercom MCP server
2. **Always Fresh Data**: Background sync keeps data current automatically  
3. **MCP Compliant**: Interface layer is stateless, internal processes handle state
4. **No External Dependencies**: No cron jobs, systemd timers, or external daemons needed
5. **Smart Clients**: ask-intercom can query data freshness and make intelligent routing decisions

This creates a self-contained MCP server that maintains fresh data while providing a clean, stateless interface to clients!
