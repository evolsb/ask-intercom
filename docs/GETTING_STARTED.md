# Getting Started with Ask-Intercom Development

> **Quick Start Guide:** Everything you need to know to jump into Ask-Intercom development

## 🎯 Current Status & Next Steps

### Where We Are
- **✅ Phase 0 Complete**: Functional CLI prototype with customer intelligence capabilities
- **🔄 Phase 0.5 In Progress**: MCP integration planning for <10 second response time
- **🚀 Strategic Direction**: Universal Customer Intelligence Agent for agent marketplaces

### What to Do Next
1. **Read the Architecture Decision**: [`docs/architecture/universal-agent-design.md`](architecture/universal-agent-design.md)
2. **Review MCP Implementation Plan**: [`docs/mcp/integration-plan.md`](mcp/integration-plan.md)  
3. **Test Current System**: `env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "show me issues from the last 24 hours"`

## 📋 Essential Reading Order

### 1. Strategic Context (Start Here)
- **[`docs/vision.md`](vision.md)** - North star: Universal Customer Intelligence Agent
- **[`docs/architecture/universal-agent-design.md`](architecture/universal-agent-design.md)** - Key architectural decision (Universal Agent vs Multi-Agent)
- **[`PROGRESS.md`](../PROGRESS.md)** - Development status and next priorities

### 2. Implementation Guidance
- **[`docs/mcp/integration-plan.md`](mcp/integration-plan.md)** - Detailed 3-week MCP implementation plan
- **[`docs/build-progression.md`](build-progression.md)** - Phase-by-phase development strategy
- **[`CLAUDE.md`](../CLAUDE.md)** - Developer setup and common commands

### 3. Reference & Future Planning
- **[`docs/backlog.md`](backlog.md)** - Strategic opportunities and future features
- **[`docs/mcp/setup-guide.md`](mcp/setup-guide.md)** - MCP technical setup details
- **[`docs/mcp/testing-framework.md`](mcp/testing-framework.md)** - Testing strategy for MCP

## 🏗️ Development Phases Overview

| Phase | Status | Goal | Timeline |
|-------|--------|------|----------|
| **Phase 0** | ✅ Complete | CLI prototype with customer intelligence | Complete |
| **Phase 0.5** | 🔄 Current | MCP integration + <10s response time | 3-4 weeks |
| **Phase 1** | 🔮 Planned | Universal Agent skills architecture | Q3 2025 |
| **Phase 2** | 🔮 Planned | Multi-platform intelligence (+ Slack MCP) | Q4 2025 |
| **Phase 3** | 🔮 Planned | Strategic intelligence (+ Linear MCP) | Q1 2026 |
| **Phase 4** | 🔮 Planned | Agent marketplace deployment | Q2 2026 |

## 🛠️ Quick Development Setup

### Prerequisites
```bash
# Ensure you have the right Python and Poetry
/opt/homebrew/bin/python3 --version  # Should be 3.13.3
~/.local/bin/poetry --version         # Should be 2.1.3
```

### Test Current System
```bash
# Test the CLI with a clean environment
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "what are the top customer complaints this month?"

# View debug logs
tail -f .ask-intercom-dev/debug.log

# Run tests
~/.local/bin/poetry run pytest -v
```

### Key Commands
```bash
# Install dependencies
~/.local/bin/poetry install

# Run CLI with debug output
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli --debug "your query"

# Run integration tests
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python tests/integration/test_timeframe_consistency.py

# Pre-commit quality checks
~/.local/bin/poetry run pre-commit run --all-files
```

## 🎯 Phase 0.5 Implementation Priorities

### Week 1: MCP Client Foundation
- [ ] Create `src/mcp_client.py` with connection management
- [ ] Add MCP configuration to `src/config.py`
- [ ] Implement dual-mode operation in `src/intercom_client.py`
- [ ] Design interfaces for future multi-MCP support

### Week 2: Conversation Fetching via MCP
- [ ] Implement MCP tool integration for conversation fetching
- [ ] Ensure data parity with REST API responses
- [ ] Add performance optimization and error handling
- [ ] Prepare cross-platform context management

### Week 3: Testing & Benchmarking
- [ ] Create comprehensive MCP vs REST performance tests
- [ ] Implement automated benchmarking suite
- [ ] Validate <10 second response time target
- [ ] Document performance improvements

## 🚀 Universal Agent Vision

### Current Capability
```
Query: "What are the top customer complaints this month?"
Source: Intercom (REST API)
Response: Customer intelligence insights
```

### Phase 2 Target Capability
```
Query: "What customer issues are our team discussing in Slack?"
Sources: Intercom MCP + Slack MCP
Response: Cross-platform customer + team intelligence
```

### Phase 3 Target Capability
```
Query: "What on our roadmap should be deprioritized according to customer feedback?"
Sources: Intercom MCP + Slack MCP + Linear MCP
Response: Strategic intelligence across customer + team + product
```

### Phase 4 Target Capability
```
Deployment: "Universal Customer Intelligence Agent" in Claude Apps, GPT Store
Configuration: User connects any MCP-enabled platforms (Intercom, Zendesk, HubSpot, Slack, Linear, etc.)
Value: First universal agent for customer intelligence across any platform combination
```

## ⚡ Quick Decision Reference

### ✅ Decided (Implemented)
- Universal Agent architecture over Multi-Agent Orchestra
- CLI prototype with REST API integration
- Performance optimization through conversation compression
- Deterministic timeframe parsing over AI-based parsing

### 🔄 Deciding Now (Phase 0.5)
- MCP client implementation approach
- Dual-mode operation architecture details
- Performance benchmarking methodology
- Universal agent interface design

### 🔮 Future Decisions
- Slack MCP integration approach (Phase 2)
- Linear MCP integration strategy (Phase 3)
- Agent marketplace deployment details (Phase 4)
- Cross-platform correlation algorithms

## 🧭 Key Architecture Principles

1. **Universal Agent Focus**: Single agent with pluggable skills, not multiple specialized agents
2. **MCP-First Strategy**: Standardized protocol for future-proof platform integration
3. **Cross-Platform Intelligence**: Unique value through multi-platform data correlation
4. **Agent Marketplace Ready**: Built for deployment as "Universal Customer Intelligence Agent"
5. **Performance-Conscious**: <10 second response time for excellent user experience

## 📞 Getting Help

- **Developer Setup**: See [`CLAUDE.md`](../CLAUDE.md) for environment setup and common commands
- **Architecture Questions**: Review [`docs/architecture/universal-agent-design.md`](architecture/universal-agent-design.md)
- **Implementation Details**: Check [`docs/mcp/integration-plan.md`](mcp/integration-plan.md)
- **Current Status**: Always check [`PROGRESS.md`](../PROGRESS.md) for latest development status

---

**Ready to contribute?** Start with Phase 0.5 MCP implementation - the foundation for our Universal Customer Intelligence Agent!
