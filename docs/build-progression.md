# Build Progression – Risk-First Development

> **What this document is:** The technical roadmap for building Ask-Intercom. Breaks down development into phases that de-risk the hardest problems first. Use this as your implementation guide with clear success criteria for each phase.

> _Prioritize the riskiest technical challenges first to prove viability, then layer on user experience._

---

## Risk Assessment & Mitigation Strategy

**Highest Risk (prove first):**
1. Intercom MCP integration actually works
2. LLM can generate meaningful insights from conversation data
3. Vector search retrieves relevant context
4. Cost/latency is acceptable for real queries

**Medium Risk (solve after core proven):**
- Slack bot integration & OAuth flows
- Scheduling infrastructure
- Multi-tenant data isolation

**Low Risk (polish phase):**
- UI/UX refinements
- Advanced querying features
- Billing integration

---

## Build Order: 4 Proof Points

### 🔬 **Phase 0: Core Intelligence Proof** _(Week 1-2)_
**Goal:** Prove the AI + MCP integration can answer one question well

**Deliverable:** CLI script that can answer "What are the top customer complaints this month?"

**Technical scope:**
- Basic Python CLI with argparse
- Intercom MCP client integration with date filtering
- OpenAI API integration (gpt-4) with function calling for timeframe interpretation
- Agentic prompt engineering: AI interprets timeframes ("this week" → 7 days) and calls appropriate tools
- No persistence, no scheduling, no UI

**Success criteria:**
- Connects to Intercom via MCP with dynamic date filtering
- AI correctly interprets timeframes ("this week" vs "recent" vs "last quarter")
- Fetches appropriate conversation window based on query context
- Generates a coherent 3-5 bullet summary
- Runs in <10 seconds
- Costs <$0.50 per query

**Risk mitigation:** If MCP doesn't work or is too slow, fallback to direct Intercom API

---

### 🧠 **Phase 1: Context & Memory** _(Week 3)_
**Goal:** Prove vector search improves answer quality

**Deliverable:** Enhanced CLI with semantic search and conversation context

**Technical scope:**
- Add pgvector to Postgres database
- Implement conversation chunking and embedding
- RAG pipeline: retrieve → context → generate
- Support follow-up questions with memory

**Success criteria:**
- Answers improve when referencing older conversations
- Can handle queries like "What did john@company.com complain about last quarter?"
- Vector search retrieves relevant context 80%+ of the time

**Risk mitigation:** Start simple with sentence-transformers, upgrade to better embeddings if needed

---

### 💬 **Phase 2: Slack Integration** _(Week 4)_
**Goal:** Prove users will actually use it in their workflow

**Deliverable:** Working `/askintercom` Slack command with Docker deployment

**Technical scope:**
- FastAPI web server for Slack webhooks
- Slack app installation flow with proper OAuth scopes
- Bot token management per workspace
- Threaded responses for better UX
- Docker containerization for easy deployment
- Environment variable configuration (no external dependencies)

**Success criteria:**
- Test team uses it 3+ times per week
- Average response time < 5 seconds
- Positive feedback on answer quality
- Docker deployment works on first try

**Risk mitigation:** If Slack is complex, use simple webhook without fancy OAuth first

---

### ⚡ **Phase 3: Automation Basics** _(Week 5-6)_
**Goal:** Prove scheduled insights create ongoing value

**Deliverable:** Simple scheduled digest system

**Technical scope:**
- Celery/Redis for job scheduling
- YAML-based alert configuration (Phase 3), evolving to Slack-native config later
- Weekly digest: "angry customers summary"
- Slack delivery of scheduled reports
- Basic error handling and retries

**Success criteria:**
- Weekly digest runs reliably
- Team stops asking for manual reports
- Clear ROI on time saved

---

### ⚡ **Phase 3: Strategic Intelligence** _(Q1 2026)_
**Goal:** Add Linear MCP for strategic roadmap correlation

**Deliverable:** Strategic intelligence queries spanning customer, team, and product data

**Technical Scope:**
- Linear MCP integration for roadmap data
- Strategic correlation algorithms
- "What should we deprioritize based on customer feedback?" capabilities
- Cross-platform strategic analysis

**Success Criteria:**
- Linear MCP integration complete
- Strategic queries working across all three platforms
- Unique strategic insights demonstrable
- Clear competitive differentiation achieved

**Strategic Value:** Only agent providing customer + team + product strategic intelligence

### 🏪 **Phase 4: Agent Marketplace Deployment** _(Q2 2026)_
**Goal:** Deploy "Universal Customer Intelligence Agent" to agent marketplaces

**Deliverable:** Marketplace-ready agent with standardized MCP configuration

**Technical Scope:**
- Agent marketplace packaging and deployment
- User-friendly MCP connection configuration
- Multi-platform agent wrappers (Claude Apps, GPT Store, etc.)
- Revenue sharing integration

**Success Criteria:**
- "Universal Customer Intelligence Agent" deployed to major marketplaces
- Users can connect any MCP-enabled platform without custom development
- Clear competitive positioning as universal solution
- Revenue generation from agent marketplace presence

**Strategic Value:** First universal customer intelligence agent in marketplaces

---

## Decision Points & Fallbacks

**If Intercom MCP fails:**
- Fall back to REST API with pagination
- Accept slower performance, plan optimization later

**If vector search is too complex:**
- Start with simple text matching and filtering
- Add semantic search as Phase 1.5

**If costs are too high:**
- Switch to Claude-3.5-Sonnet or Llama
- Add query caching and result memoization

**If Slack integration is blocked:**
- Build simple web UI first
- Use webhook integrations instead of full OAuth

---

## Success Gates

Each phase must pass before proceeding:

- **Phase 0 Gate:** Demo one perfect answer to a real question
- **Phase 1 Gate:** Answers improve measurably with more context
- **Phase 2 Gate:** Docker deployment works + team uses it organically
- **Build-in-public Gate:** After Docker success, share progress publicly for community feedback
- **Phase 3 Gate:** First scheduled report saves manual work
- **Phase 4 Gate:** Choose monetization path based on community feedback and usage patterns

---

## Tech Stack Evolution

```
Phase 0: Python CLI + OpenAI + MCP
         ↓
Phase 1: + pgvector + embeddings
         ↓
Phase 2: + FastAPI + Slack SDK + Docker
         ↓
Phase 3: + Celery + Redis + scheduling
         ↓
Phase 4: + SaaS hosting OR agent marketplace (user choice)
```

**Key principle:** Add complexity only when the previous layer is proven and working well.

---

_Last updated: Jun 16 2025_
