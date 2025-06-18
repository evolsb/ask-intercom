# MCP Integration Plan for Ask-Intercom

> **Status**: Phase 0.5 - MCP Integration Planning  
> **Goal**: Implement dual-mode operation (REST + MCP) with performance/quality comparison  
> **Priority**: High - Target <10 second response time

## Executive Summary

Integrate Intercom's Model Context Protocol (MCP) as an alternative to REST API for conversation fetching, while maintaining REST as fallback. Implement comprehensive testing to compare performance and quality between approaches.

## MCP Background & Benefits

### Model Context Protocol Overview
- **What**: Standardized protocol for AI applications to access data sources
- **Architecture**: Client-server model with persistent connections
- **Intercom Implementation**: Remote MCP server at `https://mcp.intercom.com/sse`
- **Authentication**: OAuth-based workspace authorization

### Expected Performance Benefits
- **Connection Efficiency**: Persistent connection vs per-request HTTP overhead
- **Data Streaming**: Real-time conversation streaming vs batch fetching
- **Selective Fields**: Request only needed data vs full conversation objects
- **Estimated Improvement**: 30-50% reduction in API fetch time (10s → 3-5s)

### References
- [Intercom MCP Documentation](https://developers.intercom.com/docs/guides/mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/introduction)
- [Third-party MCP Intercom Server](https://github.com/fabian1710/mcp-intercom)

## Technical Architecture

### Dual-Mode Operation Design

```python
class ConversationFetcher:
    def __init__(self, config):
        self.rest_client = IntercomClient(config.intercom_token)
        self.mcp_client = MCPIntercomClient(config) if config.enable_mcp else None
        
    async def fetch_conversations(self, filters):
        if self.mcp_client and self.mcp_client.is_connected():
            try:
                return await self.mcp_client.fetch_conversations(filters)
            except Exception as e:
                logger.warning(f"MCP failed, falling back to REST: {e}")
                
        return await self.rest_client.fetch_conversations(filters)
```

### MCP Client Implementation Strategy

1. **Connection Management**
   - Persistent WebSocket/SSE connection to `mcp.intercom.com/sse`
   - Automatic reconnection with exponential backoff
   - Connection health monitoring and failover

2. **Authentication Flow**
   - OAuth workspace authorization (one-time setup)
   - Token refresh management
   - Secure credential storage

3. **Conversation Fetching**
   - Stream conversations matching filters
   - Parse MCP tool responses to `Conversation` objects
   - Handle pagination through MCP protocol

4. **Error Handling & Fallback**
   - Connection failures → REST API fallback
   - Rate limiting → Graceful degradation
   - Partial failures → Continue with available data

## Implementation Plan

### Phase 0.5.1: MCP Client Foundation (Week 1)

**Goal**: Basic MCP client with connection management

**Tasks**:
1. **Add MCP Dependencies**
   ```bash
   # Add to pyproject.toml
   mcp-client = "^1.0.0"  # Or appropriate MCP client library
   websockets = "^12.0"   # For WebSocket connections
   ```

2. **Create MCPIntercomClient**
   - File: `src/mcp_client.py`
   - Connection establishment and management
   - Basic authentication flow
   - Health monitoring

3. **Configuration Updates**
   - Add `ENABLE_MCP=true/false` environment variable
   - Add MCP connection settings to `Config` class
   - OAuth token storage strategy

4. **Integration Point**
   - Update `IntercomClient` to support dual-mode operation
   - Graceful fallback mechanism
   - Logging for mode selection

**Success Criteria**:
- MCP client can connect to Intercom's MCP server
- Authentication flow works correctly
- Fallback to REST API on connection failure
- Configuration flag controls MCP usage

### Phase 0.5.2: Conversation Fetching via MCP (Week 2)

**Goal**: Feature parity with REST API for conversation fetching

**Tasks**:
1. **MCP Tool Integration**
   - Implement `search-conversations` MCP tool calls
   - Map `ConversationFilters` to MCP parameters
   - Handle MCP response format

2. **Data Transformation**
   - Convert MCP responses to `Conversation` objects
   - Ensure data parity with REST API responses
   - Handle missing fields gracefully

3. **Performance Optimization**
   - Implement conversation streaming
   - Parallel conversation processing
   - Connection pooling and reuse

4. **Error Handling**
   - MCP-specific error codes and handling
   - Timeout management for long-running queries
   - Partial result handling

**Success Criteria**:
- MCP fetches same conversations as REST API
- Data transformation maintains full compatibility
- Error handling provides clear fallback behavior

### Phase 0.5.3: Testing & Benchmarking (Week 3)

**Goal**: Comprehensive performance and quality comparison

**Tasks**:
1. **Performance Testing Suite**
   - File: `tests/integration/test_mcp_vs_rest.py`
   - Side-by-side performance benchmarks
   - Multiple dataset sizes (10, 50, 100+ conversations)
   - Network latency simulation

2. **Quality Assurance Testing**
   - Conversation data accuracy comparison
   - Analysis result consistency between modes
   - Edge case handling verification

3. **Automated Benchmarking**
   - CI/CD integration for performance monitoring
   - Regression detection for both modes
   - Performance dashboard creation

4. **Documentation & Reporting**
   - Performance comparison reports
   - Quality metrics documentation
   - Troubleshooting guides

**Success Criteria**:
- Automated test suite runs both REST and MCP modes
- Performance metrics collected and compared
- Quality assurance validates identical analysis results

## Testing Strategy

### Performance Benchmarking

```python
class MCPvsRESTBenchmark:
    """Comprehensive benchmark comparing MCP vs REST performance."""
    
    async def run_benchmark(self, query: str, iterations: int = 5):
        results = {
            'rest': [],
            'mcp': []
        }
        
        for i in range(iterations):
            # Test REST API
            start_time = time.time()
            rest_result = await self.rest_client.fetch_conversations(filters)
            rest_duration = time.time() - start_time
            
            # Test MCP
            start_time = time.time()
            mcp_result = await self.mcp_client.fetch_conversations(filters)
            mcp_duration = time.time() - start_time
            
            results['rest'].append({
                'duration': rest_duration,
                'conversation_count': len(rest_result),
                'cost': estimate_cost(rest_result)
            })
            
            results['mcp'].append({
                'duration': mcp_duration,
                'conversation_count': len(mcp_result),
                'cost': estimate_cost(mcp_result)
            })
            
            # Quality comparison
            assert_conversation_equality(rest_result, mcp_result)
            
        return generate_benchmark_report(results)
```

### Test Scenarios

1. **Small Datasets** (≤20 conversations)
   - Simple queries with fast model selection
   - Low-complexity analysis requirements

2. **Medium Datasets** (20-100 conversations)
   - Complex analysis queries
   - Performance optimization validation

3. **Large Datasets** (100+ conversations)
   - Stress testing with user confirmation flow
   - Network resilience and fallback behavior

4. **Edge Cases**
   - Connection failures and recovery
   - Rate limiting scenarios
   - Partial data availability

### Quality Assurance Metrics

1. **Data Accuracy**
   - Conversation count consistency
   - Message content preservation
   - Metadata completeness

2. **Analysis Quality**
   - Identical insight generation
   - Customer identification accuracy
   - Cost estimation consistency

3. **Reliability**
   - Fallback mechanism effectiveness
   - Error recovery success rate
   - Connection stability metrics

## Expected Outcomes

### Performance Projections

**Current State (REST API)**:
- 61 conversations: 13.9s total (10s fetch + 4s analysis)
- API overhead: ~2-3s per request cycle

**Target State (MCP)**:
- 61 conversations: 8-10s total (3-5s fetch + 4s analysis)
- 30-50% improvement in fetch time
- **Achievement of <10s target** 🎯

### Risk Mitigation

1. **Connection Reliability**
   - Automatic fallback to REST API
   - Connection health monitoring
   - Graceful degradation on partial failures

2. **Authentication Complexity**
   - Clear setup documentation
   - OAuth flow error handling
   - Token refresh automation

3. **Performance Regressions**
   - Continuous benchmarking in CI/CD
   - Performance alerts for degradation
   - Quick rollback mechanism via configuration

## Implementation Files

### New Files to Create

```
src/
├── mcp_client.py              # MCP client implementation
├── mcp_auth.py                # OAuth and authentication handling
└── conversation_fetcher.py    # Dual-mode abstraction layer

tests/
├── integration/
│   ├── test_mcp_vs_rest.py    # Performance comparison suite
│   └── test_mcp_integration.py # MCP-specific integration tests
└── unit/
    └── test_mcp_client.py     # Unit tests for MCP client

docs/mcp/
├── setup-guide.md             # MCP setup and configuration
├── troubleshooting.md         # Common issues and solutions
└── performance-reports/       # Benchmark results and analysis
```

### Configuration Changes

```python
# src/config.py additions
class Config(BaseModel):
    # Existing fields...
    
    # MCP Configuration
    enable_mcp: bool = Field(default=False, description="Enable MCP client")
    mcp_server_url: str = Field(
        default="https://mcp.intercom.com/sse",
        description="MCP server endpoint"
    )
    mcp_oauth_token: str = Field(default="", description="MCP OAuth token")
    mcp_timeout: int = Field(default=30, description="MCP connection timeout")
    mcp_fallback_enabled: bool = Field(
        default=True, 
        description="Enable REST API fallback"
    )
```

## Success Criteria

### Phase 0.5 Success Gates

1. **✅ Functional Parity**
   - MCP client fetches identical conversation data as REST
   - Analysis results are consistent between modes
   - Fallback mechanism works reliably

2. **✅ Performance Target**
   - MCP mode achieves <10 second response time
   - Demonstrable improvement over REST API
   - Acceptable performance degradation during fallback

3. **✅ Quality Assurance**
   - Automated test suite validates both modes
   - Performance benchmarks integrated into CI/CD
   - Clear documentation for setup and troubleshooting

4. **✅ Production Readiness**
   - Error handling and recovery mechanisms
   - Configuration-driven mode selection
   - Monitoring and observability

## Next Steps

1. **Week 1**: Implement MCP client foundation
2. **Week 2**: Add conversation fetching capability
3. **Week 3**: Complete testing and benchmarking suite
4. **Week 4**: Documentation, optimization, and production preparation

Upon completion, Ask-Intercom will have dual-mode operation with comprehensive performance comparison, positioning it as a robust, high-performance customer support analysis tool ready for production deployment.

---

**Last Updated**: 2025-06-17  
**Next Review**: After Phase 0.5.1 completion
