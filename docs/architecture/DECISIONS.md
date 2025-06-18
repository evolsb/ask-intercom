# Architectural Decision Records (ADR)

> **Purpose**: Document key architectural decisions, alternatives considered, and rationale for choices made during Ask-Intercom development.

## ADR-001: Universal Agent vs Multi-Agent Orchestra Architecture

**Date**: 2025-06-18  
**Status**: ✅ Decided - Universal Agent  
**Context**: MCP implementation planning and agent marketplace positioning

### Decision
Build Ask-Intercom as a **Universal Customer Intelligence Agent** with pluggable skills rather than a multi-agent orchestra with specialized agents.

### Alternatives Considered

#### Option A: Multi-Agent Orchestra ❌
```python
# Specialized agents that collaborate
class CustomerInsightOrchestrator:
    def __init__(self):
        self.timeframe_agent = TimeframeAgent()
        self.conversation_agent = ConversationAgent()  
        self.sentiment_agent = SentimentAgent()
        self.trend_agent = TrendAgent()
        self.insight_agent = InsightAgent()
```

**Pros:**
- Technically elegant separation of concerns
- Each agent could be optimized for specific tasks
- Clear modularity and testing boundaries

**Cons:**
- Complex user configuration (5+ agents to set up)
- Higher cognitive load for users
- Marketplace fragmentation (compete against ourselves)
- Deployment complexity in production environments

#### Option B: Universal Agent with Pluggable Skills ✅
```python
# Single agent with composable capabilities
class UniversalCustomerAgent:
    def __init__(self, mcp_connections: Dict[str, MCPClient], skills: List[AgentSkill]):
        self.mcp_clients = mcp_connections
        self.skills = skills
        
    async def process_query(self, query: str):
        relevant_skills = self.match_skills_to_query(query)
        context = await self.gather_cross_platform_context(query)
        return await self.execute_skill_chain(query, relevant_skills, context)
```

### Rationale

1. **User Experience**: Users prefer single comprehensive analysis over managing multiple specialized agents
2. **Agent Marketplace Positioning**: Universal agents compete better than specialist collections
3. **Technical Simplicity**: Single agent simpler to deploy, configure, and maintain
4. **Future Expansion**: Easier to add new skills and MCP sources without architectural changes
5. **Cost-Effective**: Users get all capabilities in one agent vs. multiple purchases

### Consequences

**Positive:**
- Clear agent marketplace positioning as "Universal Customer Intelligence Agent"
- Simple user experience: one query → comprehensive insights
- Easy to add new platforms (Slack, Linear) without user reconfiguration
- Strong competitive differentiation

**Negative:**
- May be less modular for testing individual capabilities
- Single point of failure if core agent logic has issues
- May be harder to optimize specific skills independently

---

## ADR-002: MCP-First vs REST-First Integration Strategy

**Date**: 2025-06-18  
**Status**: ✅ Decided - Dual-Mode (REST + MCP)  
**Context**: Phase 0.5 implementation planning

### Decision
Implement **dual-mode operation** with REST API as proven fallback and MCP as performance optimization path.

### Alternatives Considered

#### Option A: REST-Only (Status Quo) ❌
- Continue with current REST API implementation
- Focus on other optimizations (caching, prompt engineering)

**Rejected Because:**
- Performance ceiling already reached (30.2s, need <10s)
- Misses opportunity to build Universal Agent foundation
- No preparation for multi-platform expansion

#### Option B: MCP-Only (High Risk) ❌
- Replace REST implementation entirely with MCP
- Bet everything on MCP performance benefits

**Rejected Because:**
- High risk if MCP doesn't deliver expected performance
- No fallback if MCP integration fails
- Unproven technology for this specific use case

#### Option C: Dual-Mode Operation ✅
- Keep proven REST implementation as fallback
- Add MCP client with automatic fallback to REST
- Compare performance and gradually shift to MCP

### Rationale

1. **Risk Mitigation**: Proven REST fallback ensures reliability
2. **Performance Opportunity**: MCP may achieve <10s target
3. **Universal Agent Foundation**: Prepares architecture for multi-MCP support
4. **Incremental Improvement**: Can measure and validate MCP benefits

---

## ADR-003: Timeframe Parsing - AI vs Deterministic

**Date**: 2025-06-17 (Implemented during Phase 0)  
**Status**: ✅ Decided - Deterministic Regex Parser  
**Context**: Timeframe interpretation inconsistency issues

### Decision
Replace AI-based timeframe parsing with **deterministic regex-based parser**.

### Problem
AI-based parsing was inconsistent:
- "1 hour" sometimes returned different date ranges
- Function calling overhead added latency
- Difficult to debug and validate

### Solution Implemented
```python
def parse_timeframe_deterministic(self, query: str) -> Optional[TimeFrame]:
    """Parse timeframe using deterministic regex patterns."""
    # Patterns for "last X hours/days/weeks/months"
    # Patterns for "this week/month/quarter"
    # Patterns for "recent" and relative terms
```

### Consequences
- ✅ Consistent timeframe interpretation
- ✅ Faster processing (no AI call needed)
- ✅ Easier to debug and validate
- ✅ Reduced cost per query

---

## ADR-004: Performance Optimization Strategy

**Date**: 2025-06-17 (Implemented during Phase 0)  
**Status**: ✅ Decided - Safe Optimization Phases  
**Context**: 51s → <10s response time target

### Decision
Implement **safe, incremental optimization phases** rather than risky architectural changes.

### Phases Implemented

#### Phase 1: Search API Migration ✅
- **Change**: Replace 50+ individual API calls with single search API call
- **Result**: 51s → 20.5s (60% improvement)
- **Risk**: Low - graceful fallback to old method

#### Phase 2: Concurrent Processing ✅
- **Change**: HTTP connection pooling and async optimization
- **Result**: 20.5s → ~20s (minimal improvement - bottleneck is AI, not API)
- **Risk**: Low - infrastructure optimization only

#### Phase 3: Conversation Compression ✅
- **Change**: Intelligent conversation summarization while preserving context
- **Result**: 51s → 30.2s baseline (40% improvement from original)
- **Risk**: Medium - quality validation required

### Alternatives Rejected (Moved to "Icebox")

#### High-Risk Optimizations ❌
- **Local conversation caching**: Complex sync requirements
- **Semantic deduplication**: Risk of losing critical insights
- **Two-stage AI analysis**: Quality concerns
- **Aggressive filtering**: Risk of eliminating valuable customer responses

### Rationale
Focus on proven, safe optimizations first. Risky optimizations require extensive quality validation and may introduce business insight loss.

---

## ADR-005: Platform Expansion Strategy

**Date**: 2025-06-18  
**Status**: ✅ Decided - MCP-First Multi-Platform  
**Context**: Universal Agent architecture planning

### Decision
Expand to multiple platforms using **MCP protocol standardization** rather than custom REST integrations.

### Expansion Roadmap

#### Phase 2: Slack MCP Integration
- **Capability**: "What customer issues are our team discussing in Slack?"
- **Value**: Customer + team intelligence correlation
- **Technology**: Slack MCP protocol

#### Phase 3: Linear MCP Integration
- **Capability**: "What should we deprioritize based on customer feedback?"
- **Value**: Strategic intelligence across customer + team + product
- **Technology**: Linear MCP protocol

### Alternatives Considered

#### Option A: REST API Custom Integrations ❌
- Build custom REST integrations for each platform
- **Rejected**: High development overhead, not future-proof

#### Option B: Single Platform Focus ❌
- Stay focused only on Intercom integration
- **Rejected**: Misses Universal Agent opportunity

#### Option C: MCP-First Strategy ✅
- Use MCP protocol for all platform integrations
- **Benefits**: Standardized integration, future-proof, universal agent positioning

---

## Icebox: Deferred Decisions

### Performance Optimizations (Deferred)
- **Conversation Caching**: Wait for MCP performance results before adding complexity
- **Semantic Deduplication**: Evaluate after universal agent implementation
- **Advanced AI Optimization**: Focus on MCP performance gains first

### Alternative Architectures (Considered but Rejected)
- **FastAPI + Slack SDK Progression**: Superseded by MCP-first universal agent strategy
- **Vector Database Integration**: Not needed for current performance targets
- **Microservices Architecture**: Universal agent approach simpler and more effective

### Platform Integration Approaches (Superseded)
- **Webhook-based Integrations**: MCP provides better standardization
- **Custom API Clients**: MCP removes need for platform-specific development
- **Plugin Architecture**: MCP protocol serves as universal plugin standard

---

**Decision Review Process**: Major architectural decisions are reviewed after each phase completion to validate assumptions and adjust course based on real-world results.
