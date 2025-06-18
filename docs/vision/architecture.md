# Universal Agent Architecture Design

> **Decision Date**: 2025-06-18  
> **Status**: Approved - Universal Agent with Pluggable Skills  
> **Context**: MCP implementation planning and agent marketplace positioning

## Executive Summary

After evaluating multi-agent orchestra vs. universal agent approaches, we've decided to build ask-intercom as a **Universal Customer Intelligence Agent** with pluggable skills and multi-MCP support. This positions us optimally for agent marketplaces while enabling comprehensive cross-platform analysis.

## Decision Context

### The Strategic Question
Should ask-intercom evolve into:
1. **Multi-Agent Orchestra**: Specialized agents (sentiment, trends, insights) that collaborate
2. **Universal Agent**: Single agent with pluggable skills and cross-platform capabilities

### Key Considerations
- **User Experience**: Users prefer single comprehensive analysis over managing multiple specialized agents
- **Agent Marketplace Positioning**: Universal agents compete better than specialist collections  
- **Technical Complexity**: Universal agent simpler to deploy, configure, and maintain
- **Future Expansion**: Need to support multiple MCP sources (Slack, Linear, etc.)

## Architectural Decision

### Universal Agent with Pluggable Skills ✅

```python
class UniversalCustomerAgent:
    """Single agent with composable capabilities across multiple data sources."""
    
    def __init__(self, mcp_connections: Dict[str, MCPClient], skills: List[AgentSkill]):
        self.mcp_clients = mcp_connections  # intercom, slack, linear, etc.
        self.skills = skills                # sentiment, trends, synthesis, etc.
        
    async def process_query(self, query: str):
        # Route to appropriate skill combinations
        relevant_skills = self.match_skills_to_query(query)
        context = await self.gather_cross_platform_context(query)
        return await self.execute_skill_chain(query, relevant_skills, context)
```

**Why This Architecture:**
- **User-Centric**: Single query → comprehensive insights across all platforms
- **Marketplace-Ready**: "Customer Intelligence Agent - Works with any MCP platform"
- **Extensible**: Add new skills and MCP sources without architectural changes
- **Cost-Effective**: Users get all capabilities in one agent vs. multiple purchases

### Rejected Alternative: Multi-Agent Orchestra ❌

While technically elegant, rejected due to:
- Complex user configuration (5+ agents to set up)
- Higher cognitive load for users
- Marketplace fragmentation (compete against ourselves)
- Deployment complexity in production environments

## Target Use Cases Enabled

### Phase 1: Enhanced Customer Intelligence
```
Query: "What are the top customer complaints this month?"
Sources: Intercom MCP
Skills: Sentiment Analysis, Trend Detection, Insight Synthesis
```

### Phase 2: Internal + External Intelligence  
```
Query: "What customer issues are our team discussing in Slack?"
Sources: Intercom MCP + Slack MCP
Skills: Cross-Platform Correlation, Team Sentiment, Issue Prioritization
```

### Phase 3: Strategic Product Intelligence
```
Query: "What on our roadmap should be deprioritized according to customer feedback?"
Sources: Intercom MCP + Linear MCP + Slack MCP
Skills: Roadmap Analysis, Customer Impact Scoring, Strategic Recommendations
```

## Technical Implementation Strategy

### Current State (Phase 0.5)
```python
# Monolithic but decomposition-ready
class QueryProcessor:
    def __init__(self):
        self.conversation_service = ConversationService()  # → Future skill
        self.analysis_service = AnalysisService()          # → Future skill  
        self.timeframe_service = TimeframeService()        # → Future skill
```

### Target State (Phase 1+)
```python
# Universal agent with pluggable architecture
class UniversalCustomerAgent:
    def __init__(self):
        self.mcp_registry = MCPRegistry()
        self.skill_registry = SkillRegistry()
        self.context_manager = CrossPlatformContextManager()
        
    async def process_query(self, query: str):
        # 1. Parse intent and identify required sources/skills
        intent = await self.parse_query_intent(query)
        
        # 2. Gather context from relevant MCP sources
        context = await self.context_manager.gather_context(intent)
        
        # 3. Execute relevant skills on cross-platform context
        return await self.skill_registry.execute_skill_chain(intent, context)
```

### Skill Architecture
```python
class AgentSkill(ABC):
    """Base class for agent capabilities."""
    
    @abstractmethod
    async def can_handle(self, query_intent: QueryIntent) -> bool:
        """Determine if this skill is relevant for the query."""
        
    @abstractmethod  
    async def execute(self, context: CrossPlatformContext) -> SkillResult:
        """Execute the skill logic."""

class SentimentAnalysisSkill(AgentSkill):
    async def can_handle(self, intent: QueryIntent) -> bool:
        return "sentiment" in intent.keywords or "complaints" in intent.keywords
        
    async def execute(self, context: CrossPlatformContext) -> SkillResult:
        # Analyze sentiment across all available conversations
        return await self.analyze_cross_platform_sentiment(context.conversations)

class RoadmapAnalysisSkill(AgentSkill):
    async def can_handle(self, intent: QueryIntent) -> bool:
        return "roadmap" in intent.keywords and context.has_linear_data()
        
    async def execute(self, context: CrossPlatformContext) -> SkillResult:
        # Correlate customer feedback with roadmap items
        return await self.correlate_feedback_to_roadmap(
            context.conversations, 
            context.roadmap_items
        )
```

### MCP Registry Architecture
```python
class MCPRegistry:
    """Manages multiple MCP connections and data source abstraction."""
    
    def __init__(self):
        self.connections = {}
        self.data_schemas = {}
        
    async def register_mcp(self, name: str, mcp_client: MCPClient):
        """Register a new MCP data source."""
        self.connections[name] = mcp_client
        self.data_schemas[name] = await mcp_client.get_schema()
        
    async def query_across_sources(self, query: DataQuery) -> CrossPlatformContext:
        """Execute query across all relevant MCP sources."""
        results = {}
        for name, client in self.connections.items():
            if query.is_relevant_for_source(name):
                results[name] = await client.execute_query(query)
        return CrossPlatformContext(results)
```

## Agent Marketplace Positioning

### Value Proposition
**"Universal Customer Intelligence Agent"**
- **Works with any MCP-enabled platform**: Intercom, Zendesk, HubSpot, Slack, Linear
- **One-click deployment**: Just connect your MCP servers, no custom integration
- **Comprehensive analysis**: Customer feedback + internal discussions + product roadmap
- **Strategic insights**: Cross-platform correlation that no single-platform tool can provide

### Competitive Advantages
1. **Zero Integration Effort**: Works with any MCP-compatible platform out of the box
2. **Cross-Platform Intelligence**: Unique insights from combining customer + internal + product data
3. **Future-Proof**: New MCP platforms automatically supported
4. **Cost-Effective**: Single agent vs. multiple specialized tools

### Target Customers
- **Product Teams**: Need customer feedback + roadmap correlation
- **Support Teams**: Need customer sentiment + internal team alignment  
- **Leadership**: Need strategic insights across customer, team, and product data

## Implementation Roadmap

### Phase 0.5: MCP Foundation (Current)
- Implement dual-mode operation (REST + MCP) for Intercom
- Maintain monolithic architecture but prepare for decomposition
- Achieve <10 second response time target

### Phase 1: Skill Architecture (Q3 2025)
- Refactor monolithic services into pluggable skills
- Implement skill registry and execution framework
- Add cross-platform context management

### Phase 2: Multi-MCP Support (Q4 2025)  
- Add Slack MCP for internal team discussions
- Implement cross-platform correlation capabilities
- Enable queries spanning customer + internal data

### Phase 3: Strategic Intelligence (Q1 2026)
- Add Linear/Roadmap MCP support
- Implement strategic analysis skills (roadmap prioritization)
- Full cross-platform strategic intelligence capabilities

### Phase 4: Agent Marketplace (Q2 2026)
- Package as standalone agent for marketplaces
- Implement user-friendly MCP configuration  
- Marketing and go-to-market for universal positioning

## Success Criteria

### Technical Success
- ✅ Single agent handles queries across multiple MCP sources
- ✅ Skills are pluggable and composable  
- ✅ Sub-10 second response time maintained across all sources
- ✅ Graceful fallback when MCP sources unavailable

### Business Success  
- ✅ Positioned as "Universal Customer Intelligence" in agent marketplaces
- ✅ Clear differentiation from single-platform competitors
- ✅ User testimonials about unique cross-platform insights
- ✅ Revenue growth from expanded use cases

## Risk Mitigation

### Technical Risks
- **MCP Complexity**: Start with proven Intercom MCP, add others incrementally
- **Performance Degradation**: Maintain fallback to REST APIs
- **Cross-Platform Data Correlation**: Start with simple use cases, evolve complexity

### Business Risks  
- **Market Timing**: MCP adoption might be slower than expected → REST API fallbacks provide immediate value
- **Competition**: Large platforms build competing universal agents → Our cross-platform focus provides moat
- **User Complexity**: Too many features confuse users → Maintain simple query interface, hide complexity

## Next Steps

1. **Complete Phase 0.5**: Finish MCP implementation plan with Intercom
2. **Validate Universal Agent Assumption**: Test current monolithic approach with users
3. **Plan Skill Decomposition**: Design skill interfaces based on current service boundaries  
4. **Research Additional MCPs**: Evaluate Slack, Linear, and other MCP implementations
5. **Agent Marketplace Research**: Study positioning and pricing of existing universal agents

---

**This architecture positions ask-intercom as a true "Universal Customer Intelligence Agent" - the first to provide comprehensive insights across customer, team, and product data through standardized MCP connections.**
