# Icebox

> **Ideas deferred or rejected** - good ideas for the wrong time

## ❄️ Deferred Until Later

### Performance Optimizations
**Why deferred**: Wait for MCP performance results before adding complexity

- **Local conversation caching**: 7s potential savings, but complex sync requirements
- **Semantic deduplication**: 5-10s savings, but risk of losing critical insights  
- **Two-stage AI analysis**: 8-12s savings, but may reduce analysis quality
- **Advanced prompt optimization**: Diminishing returns, focus on MCP gains first

### Architecture Approaches
**Why deferred**: Universal Agent approach chosen, these are alternatives

- **Vector database integration**: Not needed for current performance targets
- **Microservices architecture**: Universal agent approach simpler and more effective
- **Real-time conversation streaming**: Complex infrastructure, unclear value

### Platform Integration Methods
**Why deferred**: MCP-first strategy chosen

- **Webhook-based integrations**: MCP provides better standardization
- **Custom REST API clients**: MCP removes need for platform-specific development
- **Plugin architecture for platforms**: MCP protocol serves as universal plugin standard

## 🚫 Rejected Approaches

### Multi-Agent Orchestra Architecture
**Rejected**: 2025-06-18  
**Why**: User experience complexity, marketplace fragmentation, deployment overhead  
**Alternative chosen**: Universal Agent with pluggable skills  
**See**: [`docs/reference/decisions.md`](../reference/decisions.md) ADR-001

### MCP-Only Implementation  
**Rejected**: 2025-06-18  
**Why**: Too risky without proven fallback  
**Alternative chosen**: Dual-mode operation (REST + MCP)  
**See**: [`docs/reference/decisions.md`](../reference/decisions.md) ADR-002

### FastAPI + Slack SDK Progression
**Rejected**: 2025-06-18  
**Why**: Superseded by MCP-first universal agent strategy  
**Alternative chosen**: MCP protocol for all platform integrations

### AI-Based Timeframe Parsing
**Rejected**: 2025-06-17 (already implemented)  
**Why**: Inconsistent results, latency overhead, debugging difficulty  
**Alternative chosen**: Deterministic regex parser  
**See**: [`docs/reference/decisions.md`](../reference/decisions.md) ADR-003

## 🤔 Ideas That Might Come Back

### Enterprise Features
- Multi-tenant SaaS hosting (if agent marketplace doesn't work out)
- Custom skill development services (if demand emerges)
- White-label universal agent platform (if enterprise interest develops)

### Advanced Intelligence
- Predictive customer escalation (if core intelligence proves valuable)
- Industry-specific intelligence skills (if universal approach validates)
- Federated learning across customers (if privacy can be solved)

### Alternative Interfaces
- Web app interface (if agent marketplace adoption is slow)
- Mobile apps for insights (if usage patterns show mobile need)
- API-as-a-service (if other tools want to integrate)

---

*The icebox isn't a graveyard - ideas here might be perfect for later phases or changed circumstances*
