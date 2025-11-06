# FastIntercom MCP Sync Architecture

## The Challenge

MCP servers must be stateless, but we need to know if cached data is fresh enough for a query. How do we handle requests when FastIntercom's local database is out of sync?

## Proposed Solution: Hybrid Architecture

### 1. **Stateless MCP Server + Sync Metadata**

The MCP server remains stateless but can READ sync metadata stored in the SQLite database:

```python
# MCP server reads (doesn't maintain) sync state
def get_data_freshness(self):
    """Stateless operation - just reads metadata from DB"""
    return {
        "last_sync": "2024-06-22T20:00:00Z",
        "coverage_start": "2024-06-01T00:00:00Z", 
        "coverage_end": "2024-06-22T20:00:00Z",
        "total_conversations": 5432,
        "is_syncing": False
    }
```

### 2. **Separate Sync Daemon**

A background service maintains data freshness:

```yaml
# systemd service or cron job
fastintercom-sync-daemon:
  - Runs every 15 minutes
  - Checks for new conversations
  - Updates SQLite database
  - Writes sync metadata
  - Zero coupling with MCP server
```

### 3. **Client-Side Intelligence**

The ask-intercom client makes smart decisions:

```python
async def fetch_conversations(self, filters):
    # 1. Check FastIntercom data freshness
    freshness = await mcp.get_data_freshness()
    
    # 2. Determine if cached data covers the query
    if is_data_fresh_enough(freshness, filters):
        # Use FastIntercom MCP (fast path)
        return await mcp.search_conversations(filters)
    else:
        # Fallback to REST API (slow but fresh)
        return await self.fetch_via_rest(filters)
```

## Implementation Design

### Phase 1: Basic Freshness Check
```python
class FastIntercomMCPServer:
    """Stateless MCP server - only reads data"""
    
    async def handle_tool(self, name: str, arguments: dict):
        if name == "get_data_freshness":
            # Read-only operation from SQLite metadata table
            return self.db.get_metadata()
        
        elif name == "search_conversations":
            # Simple search - no state management
            return self.db.search(arguments)
```

### Phase 2: Sync Daemon Setup
```bash
# Install as systemd service
[Unit]
Description=FastIntercom Sync Daemon
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python -m fastintercom.sync_daemon
Restart=always
Environment="INTERCOM_TOKEN=xxx"

[Timer]
OnCalendar=*/15 * * * *
Persistent=true
```

### Phase 3: Smart Client Logic
```python
# In ask-intercom's intercom_client.py
class IntercomClient:
    async def _should_use_mcp(self, filters, freshness):
        """Decide if MCP data is fresh enough"""
        
        # If querying last 24 hours but data is 3 days old
        if filters.start_date > freshness['coverage_end']:
            return False  # Need fresh data
            
        # If data covers the query period
        if (filters.start_date >= freshness['coverage_start'] and
            filters.end_date <= freshness['coverage_end']):
            return True  # Can use cached data
            
        return False  # When in doubt, use REST
```

## Alternative Approaches Considered

### 1. **Always-On Sync** (Not Recommended)
- FastIntercom MCP runs sync on every request
- Violates stateless principle
- Poor performance

### 2. **Manual Sync Trigger** (Fallback Option)
- User manually runs `fastintercom sync` before queries
- Good for development
- Not suitable for production

### 3. **Webhook-Based Sync** (Future Enhancement)
- Intercom webhooks trigger immediate sync
- Near real-time data
- Requires webhook infrastructure

## Benefits of Proposed Architecture

1. **MCP Compliance**: Server remains truly stateless
2. **Performance**: 400x speedup when data is fresh
3. **Reliability**: Automatic fallback to REST when needed
4. **Flexibility**: Sync frequency can be tuned
5. **Separation of Concerns**: Sync logic separate from query logic

## Configuration

```yaml
# ask-intercom config
fastintercom:
  # How stale can data be? (minutes)
  max_staleness: 60
  
  # Fallback strategy
  fallback: rest  # or 'error'
  
  # Sync daemon endpoint (future)
  sync_status_url: "http://localhost:8889/status"
```

## Migration Path

1. **Current State**: Direct imports (incorrect)
2. **Step 1**: Implement freshness check in MCP
3. **Step 2**: Add client-side decision logic  
4. **Step 3**: Deploy sync daemon
5. **Step 4**: Monitor and tune

This architecture maintains MCP principles while solving the practical sync problem.
