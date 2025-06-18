# Ask‑Intercom – Vision

> **What this document is:** The north star for Ask-Intercom. Defines what we're building, why it matters, and how it's different from existing solutions. Use this as the reference for all strategic decisions.

> _The first Universal Customer Intelligence Agent that provides comprehensive insights across customer, team, and product data through standardized MCP connections._

---

## 1 · Purpose

Build the first Universal Customer Intelligence Agent that connects customer feedback, internal team discussions, and product roadmaps through standardized MCP protocols—enabling strategic cross-platform insights that no single-platform tool can provide.

## 2 · Problem Statement

- **Scattered intelligence** – Customer insights live in Intercom, team discussions in Slack, roadmap decisions in Linear—no tool connects them

- **Platform silos** – Each tool requires custom integrations; insights are limited to single-platform data

- **Strategic blind spots** – Teams can't answer "What should we deprioritize based on customer feedback?" without manual cross-referencing


## 3 · Differentiation

|Axis|Ask‑Intercom (Universal Agent)|Traditional Single-Platform Tools|
|---|---|---|
|**Platform Coverage**|Customer + Team + Product (Intercom + Slack + Linear)|Single platform only|
|**Integration Method**|Standardized MCP protocol|Custom REST API integrations|
|**Agent Marketplace**|"Universal Customer Intelligence Agent"|Platform-specific tools|
|**Cross-Platform Insights**|"What roadmap items need customer validation?"|Limited to platform data|
|**Deployment Flexibility**|Agent marketplace + self-host + managed|Typically single deployment model|
|**Architecture**|Pluggable skills + multi-MCP registry|Monolithic single-platform design|
|**Future-Proofing**|New MCP platforms = zero integration work|Each new platform requires custom development|

## 4 · Universal Agent Use Cases

### Phase 1: Enhanced Customer Intelligence
- _"What are the top customer complaints this month?"_ (Intercom MCP)
- _"Show me escalation risks from the last week"_ (Intercom MCP)
- _"Which customers mentioned our competitor?"_ (Intercom MCP)

### Phase 2: Customer + Team Intelligence  
- _"What customer issues are our team discussing in Slack?"_ (Intercom + Slack MCP)
- _"Are support and engineering aligned on this bug?"_ (Intercom + Slack MCP)
- _"Show me customer feedback that contradicts our internal assumptions"_ (Cross-platform)

### Phase 3: Strategic Intelligence
- _"What on our roadmap should be deprioritized according to customer feedback?"_ (Intercom + Linear MCP)
- _"Which roadmap items have the most customer validation?"_ (Intercom + Linear MCP)
- _"Show me disconnects between customer requests and planned features"_ (Cross-platform)

### Phase 4: Agent Marketplace Deployment
- **One-click agent installation**: "Universal Customer Intelligence Agent"
- **Zero custom integration**: Just connect your MCP servers
- **Works with any MCP platform**: Intercom, Zendesk, HubSpot, Slack, Linear, etc.


## 5 · Universal Agent Architecture

```
Agent Marketplace  ─┐
CLI Interface     ──┼─▶  ┌─────────────────────────┐
Direct API        ─┘     │ Universal Customer      │
                         │ Intelligence Agent      │
                         └─────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              Intercom MCP    Slack MCP    Linear MCP
              (Customer)     (Team)       (Product)
```

**Universal Agent Core:**
- **MCP Registry** – Multi-platform connection management
- **Skill Architecture** – Pluggable analysis capabilities (sentiment, trends, correlation)
- **Cross-Platform Context** – Unified data model across all MCP sources
- **Query Intent Parsing** – Route queries to relevant platforms and skills

**Key Technology Choices:**
- **MCP Protocol** – Standardized connections to all data sources
- **Pluggable Skills** – Composable analysis capabilities
- **Universal Data Model** – Cross-platform context management
- **Agent Marketplace Ready** – Standardized deployment patterns

## 6 · Universal Agent Roadmap

|Phase|Deliverable|Success Signal|
|---|---|---|
|**0** ✅|CLI prototype with Intercom|Functional customer intelligence queries|
|**0.5** 🔄|Parallel development: MCP + Web|<10s response time + shareable web app|
|**1**|Universal Agent with pluggable skills|Skills architecture working in CLI + web|
|**2**|Multi-MCP support (Slack integration)|Customer + team intelligence queries|
|**3**|Strategic intelligence (Linear integration)|Strategic roadmap correlation queries|
|**4**|Multi-channel deployment|Agent marketplace + SaaS platform success|

## 7 · Universal Agent Monetization

**Multi-Channel Strategy** (both agent marketplace AND SaaS platform):

- **SaaS Platform** (Phase 0.5B → ongoing):
  - Web application with freemium model
  - Team collaboration and sharing features
  - Enterprise deployments and custom integrations
  - Immediate revenue while building agent marketplace presence

- **Agent Marketplace** (Phase 4 primary focus):
  - "Universal Customer Intelligence Agent" in Claude Apps, GPT Store
  - Revenue sharing with platform providers
  - Unique positioning: Works with any MCP-enabled platform

- **Enterprise Platform**:
  - White-label universal agent solutions
  - Custom MCP integration support  
  - Professional services for strategic intelligence implementation
  - Self-hosted deployments with enterprise features


## 8 · Pre‑Mortem Highlights (top 5)

1. Schema drift / rate limits break ingest → **Mitigation**: raw JSON archive, versioned loaders.

2. LLM cost spike & latency > 10 s → streaming responses, per‑workspace quota.

3. Scheduler duplicates jobs on restart → idempotent run‑locks.

4. Slack review rejects scopes → least‑privilege OAuth & security white‑paper.

5. Multi‑tenant leak via shared cache → tenant prefix & automated secret scans.


## 9 · Universal Agent Success Metrics

**Performance Targets:**
- Response time < 10 seconds for cross-platform queries
- Cost per query < $0.50 including multi-platform data
- Accuracy ≥ 90% for strategic correlation insights

**Adoption Metrics:**
- Agent marketplace downloads and active installations
- Cross-platform query adoption (vs single-platform usage)
- Strategic intelligence query frequency

**Business Success:**
- Position as #1 "Customer Intelligence" agent in marketplaces
- Revenue from universal agent positioning
- Platform expansion rate (new MCP integrations)


---

_Document version 2.0 – Jun 18 2025. Updated for Universal Agent Architecture._
