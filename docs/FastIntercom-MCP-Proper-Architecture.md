# FastIntercom MCP - Proper Stateless Architecture

## The Problem You Identified

The current design incorrectly assumes ask-intercom can read FastIntercom's SQLite file directly. This breaks when:
- FastIntercom MCP runs on a different server
- FastIntercom MCP runs in a container
- FastIntercom MCP runs as a cloud service

## Correct Solution: MCP Tools for Metadata

### 1. **Add MCP Tools for Metadata**

FastIntercom MCP should expose metadata through its tool interface:

```typescript
// FastIntercom MCP server exposes these tools
tools: [
  {
    name: "get_data_info",
    description: "Get information about cached data",
    parameters: {},
    returns: {
      last_sync: "2024-06-22T20:00:00Z",
      data_age_minutes: 45,
      coverage_start: "2024-06-01T00:00:00Z",
      coverage_end: "2024-06-22T20:00:00Z",
      total_conversations: 5432,
      database_size_mb: 124.5
    }
  },
  {
    name: "check_coverage",
    description: "Check if cached data covers a date range",
    parameters: {
      start_date: "2024-06-20T00:00:00Z",
      end_date: "2024-06-22T00:00:00Z"
    },
    returns: {
      has_coverage: true,
      coverage_gaps: [],
      data_age_minutes: 45
    }
  },
  {
    name: "search_conversations",
    description: "Search cached conversations",
    parameters: { /* ... */ }
  }
]
```

### 2. **Client-Side Implementation**

```python
class IntercomClient:
    async def fetch_conversations(self, filters):
        if self.mcp_adapter:
            try:
                # Ask MCP server about its data (over network)
                data_info = await self.mcp_adapter.call_tool(
                    "get_data_info", 
                    {}
                )
                
                # Check if data covers our query
                coverage = await self.mcp_adapter.call_tool(
                    "check_coverage",
                    {
                        "start_date": filters.start_date.isoformat(),
                        "end_date": filters.end_date.isoformat()
                    }
                )
                
                # Make decision based on MCP response
                if coverage["has_coverage"] and data_info["data_age_minutes"] < 60:
                    # Use MCP for data
                    return await self.mcp_adapter.call_tool(
                        "search_conversations",
                        filters.to_dict()
                    )
                else:
                    # Fall back to REST
                    logger.info(f"MCP data too old or incomplete, using REST")
                    return await self._fetch_via_rest(filters)
                    
            except Exception as e:
                # MCP unavailable, use REST
                return await self._fetch_via_rest(filters)
```

### 3. **FastIntercom MCP Server Implementation**

```python
class FastIntercomMCPServer:
    async def handle_get_data_info(self, params):
        """Stateless - just reads current state"""
        # Read from SQLite metadata table
        metadata = self.db.query("SELECT * FROM sync_metadata ORDER BY id DESC LIMIT 1")
        
        return {
            "last_sync": metadata["last_sync"],
            "data_age_minutes": (datetime.now() - metadata["last_sync"]).seconds / 60,
            "coverage_start": metadata["coverage_start"],
            "coverage_end": metadata["coverage_end"],
            "total_conversations": metadata["total_conversations"]
        }
    
    async def handle_check_coverage(self, params):
        """Check if we have data for the requested range"""
        metadata = self.db.query("SELECT * FROM sync_metadata ORDER BY id DESC LIMIT 1")
        
        query_start = datetime.fromisoformat(params["start_date"])
        query_end = datetime.fromisoformat(params["end_date"])
        
        has_coverage = (
            query_start >= metadata["coverage_start"] and
            query_end <= metadata["coverage_end"]
        )
        
        return {
            "has_coverage": has_coverage,
            "data_age_minutes": (datetime.now() - metadata["last_sync"]).seconds / 60
        }
```

## Benefits of This Approach

1. **Truly Distributed**: MCP server can run anywhere
2. **MCP Compliant**: All communication via MCP protocol
3. **Stateless**: Server only reads and returns current state
4. **Network Transparent**: Works over TCP, stdio, or any MCP transport
5. **Clean Separation**: No filesystem coupling between services

## Architecture Diagram

```
┌─────────────────┐                    ┌──────────────────┐
│  Ask-Intercom   │                    │ FastIntercom MCP │
│   (Any Server)  │◄──── MCP Proto ───►│  (Any Server)    │
│                 │                    │                  │
│ 1. get_data_info│                    │ ┌──────────────┐ │
│ 2. check_coverage                    │ │   SQLite DB  │ │
│ 3. search_convos│                    │ │ + metadata   │ │
└─────────────────┘                    │ └──────────────┘ │
                                       └──────────────────┘
```

## Migration Path

1. FastIntercom MCP adds `get_data_info` and `check_coverage` tools
2. Ask-intercom queries these tools before deciding to use MCP
3. Remove all filesystem-based freshness checking
4. Both services can now run anywhere

This is the correct, MCP-compliant architecture!
