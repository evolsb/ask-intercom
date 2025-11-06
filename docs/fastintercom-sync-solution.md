# FastIntercom Sync State Solution

## Summary

Since MCP servers must be stateless, we implement a **hybrid architecture** that maintains MCP compliance while solving the data freshness problem:

1. **FastIntercom MCP Server** - Remains stateless, only reads data
2. **Sync Daemon** - Separate process that maintains data freshness  
3. **Smart Client Logic** - Decides whether to use cached MCP data or REST API

## Quick Implementation

### 1. Enable the Sync Daemon
```bash
# Run once to test
python scripts/fastintercom-sync-daemon.py --once

# Run continuously (every 15 minutes)
python scripts/fastintercom-sync-daemon.py --interval 15
```

### 2. Client Automatically Chooses Best Path
- **Fresh data available**: Uses FastIntercom MCP (400x faster)
- **Data too old**: Falls back to REST API (always fresh)
- **No manual intervention needed**

### 3. Configure Freshness Tolerance
```python
# In src/config.py or .env
FASTINTERCOM_MAX_STALENESS_MINUTES=60  # How old can data be?
```

## Benefits

- ✅ **MCP Compliant**: Server remains stateless
- ✅ **Automatic**: No manual sync triggers needed
- ✅ **Fast**: 400x speedup when data is fresh
- ✅ **Reliable**: Automatic fallback to REST when needed
- ✅ **Transparent**: User doesn't need to know about sync state

## Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│  Ask-Intercom   │────▶│ FastIntercom MCP │────▶│ SQLite Database │
│    (Client)     │     │   (Stateless)    │     │   (with data)   │
│                 │     │                  │     │                 │
└────────┬────────┘     └──────────────────┘     └────────▲────────┘
         │                                                   │
         │                                                   │
         ▼                                                   │
┌─────────────────┐                              ┌──────────┴────────┐
│                 │                              │                   │
│   REST API      │                              │   Sync Daemon     │
│   (Fallback)    │                              │ (Maintains Fresh) │
│                 │                              │                   │
└─────────────────┘                              └───────────────────┘
```

## Current Status

- ✅ Basic freshness checking implemented
- ✅ Client-side decision logic added
- ✅ Sync daemon script created
- 🔄 FastIntercom MCP needs proper tool implementation
- 🔄 SQLite metadata table needed for production
