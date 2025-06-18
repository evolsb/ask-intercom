# MCP Setup Guide for Ask-Intercom

> **Prerequisites**: Phase 0.5 MCP integration must be implemented first  
> **Audience**: Developers and system administrators  
> **Estimated Setup Time**: 15-30 minutes

## Quick Start

### 1. Enable MCP in Configuration

Add to your `.env` file:
```bash
# MCP Configuration
ENABLE_MCP=true
MCP_SERVER_URL=https://mcp.intercom.com/sse
MCP_OAUTH_TOKEN=your_oauth_token_here
MCP_TIMEOUT=30
MCP_FALLBACK_ENABLED=true
```

### 2. Test MCP Connection

```bash
# Test MCP mode specifically
env -i HOME="$HOME" PATH="$PATH" ENABLE_MCP=true ~/.local/bin/poetry run python -m src.cli "show me issues from the last 1 hour"

# Test with fallback disabled to verify MCP works
env -i HOME="$HOME" PATH="$PATH" ENABLE_MCP=true MCP_FALLBACK_ENABLED=false ~/.local/bin/poetry run python -m src.cli "test query"
```

### 3. Run Performance Comparison

```bash
# Run benchmark comparing both modes
~/.local/bin/poetry run python tests/integration/test_mcp_vs_rest.py

# Generate performance report
~/.local/bin/poetry run python scripts/generate_performance_report.py
```

## Detailed Setup Instructions

### OAuth Token Acquisition

1. **For Intercom Workspaces (US only)**:
   - Visit [Intercom Developer Console](https://developers.intercom.com/building-apps/docs/oauth)
   - Create new OAuth app with MCP permissions
   - Complete authorization flow for your workspace
   - Copy OAuth token to `.env` file

2. **For Claude.ai Integration**:
   ```
   Server URL: https://mcp.intercom.com/sse
   Workspace: Select your Intercom workspace
   Permissions: Review and accept conversation access
   ```

3. **For Development/Testing**:
   - Use third-party MCP server: https://github.com/fabian1710/mcp-intercom
   - Follow repository setup instructions
   - Configure local MCP server endpoint

### Configuration Options

```bash
# Core MCP Settings
ENABLE_MCP=true                           # Enable/disable MCP client
MCP_SERVER_URL=https://mcp.intercom.com/sse  # Official Intercom MCP server
MCP_OAUTH_TOKEN=oauth_token_here          # OAuth authorization token
MCP_TIMEOUT=30                            # Connection timeout in seconds

# Fallback Behavior  
MCP_FALLBACK_ENABLED=true                 # Allow REST API fallback
MCP_RETRY_ATTEMPTS=3                      # Retry attempts before fallback
MCP_RETRY_DELAY=1                         # Delay between retries (seconds)

# Performance Tuning
MCP_CONNECTION_POOL_SIZE=5                # Max concurrent connections
MCP_STREAM_BATCH_SIZE=10                  # Conversations per batch
MCP_KEEPALIVE_INTERVAL=30                 # Connection keepalive (seconds)

# Development/Debug
MCP_DEBUG_LOGGING=false                   # Enable verbose MCP logs
MCP_PERFORMANCE_TRACKING=true             # Track performance metrics
```

### Environment-Specific Configuration

#### Production
```bash
ENABLE_MCP=true
MCP_FALLBACK_ENABLED=true
MCP_RETRY_ATTEMPTS=3
MCP_DEBUG_LOGGING=false
```

#### Development
```bash
ENABLE_MCP=true
MCP_FALLBACK_ENABLED=true
MCP_DEBUG_LOGGING=true
MCP_PERFORMANCE_TRACKING=true
```

#### Testing/CI
```bash
ENABLE_MCP=true
MCP_FALLBACK_ENABLED=false  # Test MCP exclusively
MCP_DEBUG_LOGGING=true
```

## Verification & Testing

### Connection Verification

```python
# Quick connection test
from src.mcp_client import MCPIntercomClient
from src.config import Config

config = Config.from_env()
mcp_client = MCPIntercomClient(config)

# Test connection
assert await mcp_client.test_connection()
print("✅ MCP connection successful")

# Test conversation fetching
conversations = await mcp_client.fetch_conversations(
    filters=ConversationFilters(limit=5)
)
print(f"✅ Fetched {len(conversations)} conversations via MCP")
```

### Performance Validation

```bash
# Compare REST vs MCP performance
time env ENABLE_MCP=false ~/.local/bin/poetry run python -m src.cli "test query"  # REST
time env ENABLE_MCP=true ~/.local/bin/poetry run python -m src.cli "test query"   # MCP

# Expected result: MCP should be 30-50% faster
```

### Quality Assurance

```bash
# Verify identical results between modes
~/.local/bin/poetry run python tests/integration/test_mcp_quality.py

# Output should show:
# ✅ Conversation counts match
# ✅ Message content identical  
# ✅ Analysis results consistent
# ✅ Customer identification accurate
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```
Error: Cannot connect to MCP server
```
**Solutions**:
- Verify `MCP_SERVER_URL` is correct
- Check network connectivity to mcp.intercom.com
- Ensure OAuth token is valid and not expired
- Try with `MCP_FALLBACK_ENABLED=true` to use REST as backup

#### 2. Authentication Failed
```
Error: MCP authentication failed
```
**Solutions**:
- Refresh OAuth token in Intercom Developer Console
- Verify workspace is US-hosted (MCP requirement)
- Check token permissions include conversation access
- Test with curl: `curl -H "Authorization: Bearer $TOKEN" https://mcp.intercom.com/sse`

#### 3. Performance Degradation
```
Warning: MCP slower than REST API
```
**Solutions**:
- Check `MCP_CONNECTION_POOL_SIZE` setting
- Monitor network latency to MCP server
- Verify conversation batch size optimization
- Enable `MCP_DEBUG_LOGGING` to identify bottlenecks

#### 4. Partial Data Loss
```
Warning: MCP returned fewer conversations than REST
```
**Solutions**:
- Check MCP server rate limiting
- Verify conversation filters are correctly translated
- Enable `MCP_FALLBACK_ENABLED` for data completeness
- Review conversation date range filters

### Debug Mode

Enable comprehensive debugging:
```bash
MCP_DEBUG_LOGGING=true
MCP_PERFORMANCE_TRACKING=true
LOG_LEVEL=DEBUG

# Run with debug output
~/.local/bin/poetry run python -m src.cli "debug query" 2>&1 | tee mcp_debug.log
```

### Performance Monitoring

```bash
# Generate performance comparison report
~/.local/bin/poetry run python scripts/mcp_performance_report.py

# Output includes:
# - Connection establishment time
# - Conversation fetch duration  
# - Data transfer efficiency
# - Error rates and fallback frequency
# - Cost comparison between modes
```

## Advanced Configuration

### Custom MCP Server

For development or custom deployments:
```bash
# Use local or custom MCP server
MCP_SERVER_URL=http://localhost:8000/mcp
MCP_AUTH_TYPE=api_key  # Instead of oauth
MCP_API_KEY=your_api_key_here
```

### Load Balancing

For high-throughput deployments:
```bash
# Multiple MCP server endpoints
MCP_SERVER_URLS=https://mcp1.intercom.com/sse,https://mcp2.intercom.com/sse
MCP_LOAD_BALANCE_STRATEGY=round_robin  # or 'least_connections'
```

### Monitoring Integration

```bash
# Prometheus metrics export
MCP_METRICS_ENABLED=true
MCP_METRICS_PORT=9090

# Health check endpoint
MCP_HEALTH_CHECK_ENABLED=true
MCP_HEALTH_CHECK_INTERVAL=60
```

## Migration Strategy

### Gradual Rollout

1. **Phase 1**: Enable MCP with fallback in development
2. **Phase 2**: A/B test MCP vs REST with real queries  
3. **Phase 3**: Enable MCP by default with REST fallback
4. **Phase 4**: Make MCP primary with REST as emergency fallback

### Rollback Plan

```bash
# Immediate rollback to REST-only
ENABLE_MCP=false

# Graceful rollback with monitoring
ENABLE_MCP=true
MCP_FALLBACK_ENABLED=true
MCP_FALLBACK_THRESHOLD=0.1  # Fallback if >10% failures
```

---

**Next**: See [troubleshooting.md](troubleshooting.md) for detailed problem resolution  
**Related**: [integration-plan.md](integration-plan.md) for implementation details
