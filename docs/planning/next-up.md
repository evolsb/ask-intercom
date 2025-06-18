# Next Up

> **What happens after current focus** - medium detail planning

## 🎯 Phase 1: Universal Agent Skills Architecture

**When**: After Phase 0.5 MCP integration complete  
**Goal**: Transform monolithic CLI into Universal Agent with pluggable skills  
**Timeline**: Rough estimate 4-6 weeks of vibe coding

### 🧩 Key Components to Build

#### Skill Registry & Execution
```python
class UniversalCustomerAgent:
    def __init__(self):
        self.mcp_registry = MCPRegistry()      # Multi-platform connections
        self.skill_registry = SkillRegistry()  # Pluggable capabilities
        self.context_manager = CrossPlatformContextManager()
```

#### Core Skills to Extract
- **TimeframeSkill**: Date parsing and interpretation (already mostly done)
- **ConversationSkill**: Fetching and filtering conversations
- **SentimentSkill**: Analysis of customer sentiment 
- **TrendSkill**: Pattern detection and trend analysis
- **InsightSkill**: Synthesis and recommendation generation

### 🎯 Success Criteria
- Current CLI functionality preserved but architected as skills
- Easy to add new skills without changing core agent
- MCP registry supports multiple platform connections (prep for Phase 2)
- Cross-platform context management working (prep for Slack integration)

### 🔗 Dependencies
- ✅ Phase 0.5 MCP integration complete (dual-mode working)
- ✅ Performance <10s target achieved
- ✅ Universal Agent architecture validated

## 🔮 Phase 2: Multi-Platform Intelligence (Rough Ideas)

**When**: After Phase 1 complete  
**Goal**: Add Slack MCP for customer + team intelligence  
**Key Query**: "What customer issues are our team discussing in Slack?"

### Major Work Areas
- Slack MCP integration and authentication
- Cross-platform correlation algorithms  
- Query intent parsing (which platforms needed for this query?)
- Unified response formatting across platforms

## 🔮 Phase 3+: Strategic Intelligence (Very High Level)

**Phase 3**: Linear MCP integration → strategic roadmap queries  
**Phase 4**: Agent marketplace deployment → "Universal Customer Intelligence Agent"

---

*This gets more detailed as phases approach - no need to plan too far ahead*
