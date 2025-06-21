# Ask-Intercom Documentation

> **Transform Intercom conversations into actionable insights**

## 🚀 Quick Start

**Current Status**: Web application deployed and functional
- CLI prototype: ✅ Complete  
- Web interface: ✅ Complete
- Smart conversation limits: ✅ Removed (user-controlled optional limits)
- Real-time progress: ✅ Complete
- Production deployment: ✅ Live at https://ask-intercom-production.up.railway.app/

**Get Started**: See [02-Setup.md](02-Setup.md)

## 🔧 Production Debugging

**Live App**: https://ask-intercom-production.up.railway.app/

**Debug Endpoints**:
- Logs: `https://ask-intercom-production.up.railway.app/api/logs?lines=50`
- Health: `https://ask-intercom-production.up.railway.app/api/health`
- Debug info: `https://ask-intercom-production.up.railway.app/api/debug`

**Railway CLI**: `railway logs | grep -i "error\|json\|parse"`

## 📂 Documentation Structure

- **[02-Setup.md](02-Setup.md)** - Development environment setup
- **[03-Architecture.md](03-Architecture.md)** - System design and components  
- **[04-Current-Status.md](04-Current-Status.md)** - What works now, recent changes
- **[05-Next-Steps.md](05-Next-Steps.md)** - Planned improvements and roadmap
- **[06-Decisions.md](06-Decisions.md)** - Key technical decisions made

## 🎯 What This Does

Ask-Intercom is an AI-powered tool that analyzes your Intercom conversations to surface:
- Top customer complaints and pain points
- Feature requests and product feedback  
- Support workflow issues
- Customer sentiment trends

**Key Features**:
- Natural language queries ("show me issues from last week")
- Real-time progress tracking
- Structured insights with customer details
- Web interface + CLI tool
- Cost-optimized AI analysis

## 🏗️ Current Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Web     │    │   FastAPI        │    │   AI Analysis   │
│   Interface     │◄───┤   Backend        │◄───┤   (OpenAI)      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Intercom API   │
                       │   (Conversations)│
                       └──────────────────┘
```

## 📊 Version History

- **v0.1**: CLI prototype (complete)
- **v0.2**: Web interface (complete) 
- **v0.3**: Smart limits removal (complete)
- **v0.4**: MCP + Universal Agent + Deployment (next - see [05-Next-Steps.md](05-Next-Steps.md))
- **v0.5**: Follow-up questions + UI improvements (planned)
- **v0.6**: Multi-platform intelligence (planned)

---

*Last updated: June 20, 2025*
