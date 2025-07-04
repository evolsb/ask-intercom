# Technical Decisions

> **Key architectural choices and rationale**

## 🏗️ Architecture Decisions

### FastAPI + React Stack
**Decision**: FastAPI backend with React frontend  
**Rationale**: 
- FastAPI provides excellent async support and automatic API docs
- React gives us modern UI with real-time updates
- Both have strong ecosystems and community support
- Easy to deploy and scale

**Alternatives Considered**: Django + HTMX, Next.js full-stack  
**Date**: Early development  
**Status**: ✅ Validated

### Server-Sent Events for Real-time Updates
**Decision**: Use SSE instead of WebSockets for progress updates  
**Rationale**:
- Simpler than WebSockets for one-way communication
- Built-in browser support, no additional libraries needed
- Works well with existing HTTP infrastructure
- Easier error handling and reconnection

**Alternatives Considered**: WebSockets, polling  
**Date**: v0.2 web interface development  
**Status**: ✅ Working well

### Structured JSON AI Output  
**Decision**: Have AI return structured JSON instead of text parsing  
**Rationale**:
- Eliminates 140+ lines of fragile regex parsing
- More reliable data extraction
- Enables richer frontend features (priorities, categories, etc.)
- Fallback to legacy parsing for safety

**Alternatives Considered**: Continue with text parsing, hybrid approach  
**Date**: v0.2 AI overhaul  
**Status**: ✅ Major improvement

## 🎯 Product Decisions

### Remove Smart Limits
**Decision**: Remove automatic conversation limits, make them user-controlled  
**Rationale**:
- Smart limits were overriding user intent ("24 hours" → 30 days)
- Users prefer predictable behavior
- Optional manual limits provide control without complexity
- Simpler codebase and fewer edge cases

**Alternatives Considered**: Fix smart limit logic, hybrid approach  
**Date**: v0.3 recent session  
**Status**: ✅ User feedback positive

### No Authentication System (Yet)
**Decision**: API keys entered directly in UI, stored locally  
**Rationale**:
- Faster time to value for users
- No server-side user management complexity
- Follows "local-first" philosophy
- Can add auth later if needed for hosted version

**Alternatives Considered**: OAuth, JWT auth, server-side key storage  
**Date**: v0.2 web interface  
**Status**: ✅ Appropriate for current scale

### OpenAI GPT-4 as Primary AI
**Decision**: Use OpenAI GPT-4 for analysis, GPT-3.5-turbo for timeframes  
**Rationale**:
- GPT-4 provides better analysis quality
- GPT-3.5-turbo sufficient for simple timeframe parsing
- Cost optimization through model selection
- Market-leading performance for this use case

**Alternatives Considered**: Claude, local models, multiple model support  
**Date**: Early development  
**Status**: ✅ Good balance of cost and quality

## 🔧 Technical Implementation Choices

### Intercom Search API over List API
**Decision**: Use Search API as primary method, List API as fallback  
**Rationale**:
- Search API includes conversation content in response
- Reduces number of API calls significantly
- Better performance for typical queries
- List API as backup for edge cases

**Alternatives Considered**: List API only, hybrid approach  
**Date**: Performance optimization  
**Status**: ✅ Significant speed improvement

### Zustand for State Management
**Decision**: Use Zustand instead of Redux or Context  
**Rationale**:
- Simpler API with less boilerplate
- Good TypeScript support
- Built-in persistence for API keys
- Sufficient for current complexity

**Alternatives Considered**: Redux Toolkit, React Context, Jotai  
**Date**: v0.2 frontend development  
**Status**: ✅ Clean and effective

### Poetry for Python Dependency Management
**Decision**: Use Poetry instead of pip/requirements.txt  
**Rationale**:
- Better dependency resolution
- Lock files for reproducible builds
- Modern Python packaging standards
- Virtual environment management

**Alternatives Considered**: pip-tools, pipenv, conda  
**Date**: Project setup  
**Status**: ✅ Solid choice

## 🚫 Decisions We Reversed

### Smart Conversation Limits (REMOVED)
**Original Decision**: Automatically adjust conversation limits based on timeframe  
**Why Removed**: Confusing user experience, overrode user intent  
**New Approach**: Optional user-controlled limits  
**Impact**: Much cleaner UX and simpler codebase

### Complex Configuration Files (AVOIDED)
**Original Consideration**: YAML/JSON config files for various settings  
**Why Avoided**: Over-engineering for current needs  
**Current Approach**: Simple .env file and optional UI settings  
**Impact**: Faster setup and less complexity

## 🤔 Decisions Still Open

### MCP Integration Timeline
**Question**: When to integrate Model Context Protocol?  
**Options**: 
- Now (v0.4) - for performance gains
- Later (v1.0) - for multi-platform support
- Never - if REST APIs prove sufficient

**Current Thinking**: Evaluate based on performance needs

### Deployment Strategy ✅ **DECIDED**
**Decision**: Railway for cloud deployment  
**Rationale**:
- Excellent developer experience with Project Canvas
- Auto PR environments perfect for open source
- Template marketplace for discoverability
- Enterprise-grade scaling (112 vCPU/2TB RAM)
- Pay-as-you-go pricing aligns with agent workloads
- Built-in secrets management for API keys
- Future-proof for agent marketplace listings

**Alternatives Considered**: 
- Render (good balance but rougher DX)
- Fly.io (performance-first but steeper learning curve)
- Vercel (frontend-only, not suitable for FastAPI)
- AWS/GCP (too complex for initial launch)
- Coolify (self-hosted, no home server available)
- Heroku (expensive, legacy platform)

**Date**: December 2024  
**Status**: ✅ Ready to deploy

### Multi-platform Architecture
**Question**: How to structure for Slack, Linear, etc.?  
**Options**:
- Monolithic expansion  
- Plugin/skills architecture
- Separate tools with shared components

**Current Thinking**: Skills architecture for flexibility

## 🚀 Platform Evaluation Summary

### Railway Selection Rationale
**Why Railway Won**:
1. **Agent Marketplace Alignment**: Enterprise scaling capabilities essential for agent workloads
2. **Developer Experience**: Best-in-class for open source projects (auto PR environments)
3. **Template Ecosystem**: Built-in discovery channel for developers
4. **Security Compliance**: Meets requirements for handling API keys and customer data
5. **Cost Structure**: Pay-as-you-go model perfect for variable AI workloads
6. **Future-Proof**: Container-first architecture ready for multi-LLM expansion

**Key Decision Factors**:
- No self-hosting requirement (no home server)
- Need for professional enterprise-ready platform
- Agent marketplace listing compatibility
- Balance of simplicity and scalability
- Strong developer community and documentation

---

*Last updated: December 20, 2024 - Added Railway deployment decision*
