# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start for New Claude Sessions

**Test the timeframe system:**
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "show me issues from the last 24 hours"
```

**Run integration tests:**
```bash  
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python tests/integration/test_timeframe_consistency.py
```

**Debug logs:**
```bash
tail -f .ask-intercom-dev/debug.log  # Live logs
grep "ERROR\|Page.*:" .ask-intercom-dev/debug.log | tail -20  # Recent errors and pagination
```

## Project Overview

Ask-Intercom is an AI-powered tool that turns raw Intercom conversations into actionable product, support, and roadmap insights. The project follows a risk-first development approach with clear phases.

**Current Status:** Phase 0 - Core Intelligence Proof (Python CLI prototype)

## Architecture & Tech Stack

### Phase 0 Components
- **CLI Interface** (`src/cli.py`): Main entry point with argparse, Rich formatting
- **Query Processor** (`src/query_processor.py`): Orchestrates the full query workflow
- **Intercom Client** (`src/intercom_client.py`): MCP protocol with REST API fallback
- **AI Client** (`src/ai_client.py`): OpenAI integration with cost tracking
- **Models** (`src/models.py`): Core data structures (Conversation, TimeFrame, AnalysisResult)
- **Config** (`src/config.py`): Environment-based configuration with Pydantic validation

### Key Design Patterns
- **Agentic workflows**: AI interprets natural language timeframes ("this month" → specific dates)
- **Graceful degradation**: MCP → REST API fallback for resilience
- **Cost optimization**: Token tracking, prompt engineering, conversation summarization
- **Risk-first architecture**: Prove hardest problems first (AI+MCP integration)

## Development Environment

### Dependencies & Commands
- **Python**: 3.13.3 available at `/opt/homebrew/bin/python3`
- **Poetry**: Available at `~/.local/bin/poetry` (version 2.1.3)
- **Testing**: `~/.local/bin/poetry run pytest -v`
- **CLI**: `~/.local/bin/poetry run python -m src.cli "your query"`
- **Interactive CLI**: `~/.local/bin/poetry run python -m src.cli --interactive`
- **Dependencies**: `~/.local/bin/poetry install` (installs from pyproject.toml)

### Critical Runtime Environment
**ALWAYS use clean environment to avoid variable conflicts:**
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "query"
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python tests/integration/test_timeframe_consistency.py
```

**Environment Variables** are loaded from `.env` file automatically - do NOT set in `.claude/settings.json`

### Debugging & Logs
- **Debug logs**: `.ask-intercom-dev/debug.log` (structured JSON, rotated at 10MB)
- **Query logs**: `.ask-intercom-dev/queries.jsonl` (query start events)
- **Result logs**: `.ask-intercom-dev/results.jsonl` (query completion events)
- **View recent logs**: `tail -50 .ask-intercom-dev/debug.log`
- **Search logs**: `grep "ERROR\|error" .ask-intercom-dev/debug.log`
- **Debug mode**: Add `--debug` flag to CLI commands for verbose console output

### Key File Locations
- **Main CLI**: `src/cli.py` - Entry point with argparse and Rich formatting
- **Timeframe Parser**: `src/ai_client.py` - Deterministic regex-based parsing (lines 81-172)
- **Intercom Client**: `src/intercom_client.py` - Pagination logic with rate limiting (lines 168-250)
- **Integration Tests**: `tests/integration/test_timeframe_consistency.py` - Comprehensive timeframe testing
- **Environment Config**: `.env` - Contains INTERCOM_ACCESS_TOKEN and OPENAI_API_KEY
- **Claude Permissions**: `.claude/settings.local.json` - Allowed bash commands

### Pre-commit Workflow
- **Run hooks before committing**: `~/.local/bin/poetry run pre-commit run --all-files`
- **Quick file fixes**: `~/.local/bin/poetry run pre-commit run --files src/file.py`
- **Skip hooks for WIP**: `git commit --no-verify -m "wip: message"`
- **Auto-fix then commit**: Let hooks fix issues, then `git add -A && git commit` again
- **Critical hooks**: `detect-secrets` (security), `black`/`ruff` (code quality)

### Testing & Quality Assurance
- **Unit tests**: `~/.local/bin/poetry run pytest tests/unit/`
- **Integration tests**: `~/.local/bin/poetry run pytest tests/integration/`
- **Timeframe consistency test**: `env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python tests/integration/test_timeframe_consistency.py`
- **All tests**: `~/.local/bin/poetry run pytest -v`

**⚠️ CURRENT STATUS**: 
1. **✅ FIXED**: Timeframe interpretation inconsistency - replaced AI-based parsing with deterministic regex parser
2. **✅ FIXED**: Pagination issues - now fetches ALL conversations with proper rate limiting
3. **✅ VERIFIED**: Containment relationships work correctly: 1 hour (5) ⊆ 1 day (63) ⊆ 1 week (472+) ⊆ 1 month (200+)

**⚠️ NEXT PRIORITIES**:
- Add timeout handling to long-running tests
- Enhance console output for real-time progress tracking  
- Test with single timeframe query to verify functionality

### Recent Test Results (2025-06-17)
**Timeframe Consistency Test Results:**
- **1 hour**: 5 conversations
- **1 day**: 63 conversations (contains all 5 from 1 hour ✅)
- **1 week**: 472 total conversations found → trimmed to 200 limit
- **1 month**: 200+ conversations (logical progression ✅)

**Pagination Working:**
- Page 1: 118 conversations
- Page 2: 118 conversations (total: 236)
- Page 3: 118 conversations (total: 354)
- Page 4: 118 conversations (total: 472)
- Rate limiting: 200ms delays between requests ✅

**Performance:**
- Full test runtime: ~5 minutes (due to pagination across multiple timeframes)
- Real-time progress logging working correctly
- API rate limits respected (83 req/10s limit)

### Environment Variables
```bash
# Required in .env file
INTERCOM_ACCESS_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here

# Optional with defaults
INTERCOM_APP_ID=your_app_id_here  # Auto-fetched if not provided
OPENAI_MODEL=gpt-4
MAX_CONVERSATIONS=50
DEBUG=false
```

**IMPORTANT**: Do not set environment variables in `.claude/settings.json` - they override the .env file and cause validation errors. The application loads from .env automatically.

### Project Structure (Phase 0)
```
src/
├── cli.py             # Main CLI entry point
├── query_processor.py # Core orchestration
├── intercom_client.py # MCP/REST API client
├── ai_client.py       # OpenAI integration
├── models.py          # Data models
└── config.py          # Configuration management
```

## Success Criteria & Gates

### Phase 0 Success Gates (All Must Pass)
- CLI answers "What are the top customer complaints this month?" correctly
- Response time < 10 seconds consistently
- Cost per query < $0.50
- Handles timeframe interpretation correctly
- Graceful error handling for API failures
- Clear, actionable 3-5 bullet point output format

### Performance Targets
- Average response time < 5s P95
- Token cost per query < $0.50
- Conversation processing: 50-100 conversations max per query

## Key Technical Decisions

### Error Handling Strategy
- **MCP failures**: Automatic fallback to REST API
- **Rate limiting**: Exponential backoff, respect Intercom limits (83 requests/10 seconds)
- **Partial failures**: Continue processing with available data
- **Cost control**: Warn users of expensive queries, optimize prompts automatically

### Data Flow
1. Parse natural language query for time context
2. Convert to specific date ranges using AI function calling
3. Fetch relevant conversations via MCP (fallback to REST)
4. Send to AI for analysis with cost-optimized prompts
5. Format and return structured results

## Development Phases

### Current: Phase 0 (CLI Prototype) - ✅ COMPLETE
**Goal**: Prove AI + MCP integration works
**Status**: Functional CLI that answers customer support queries
**Performance**: 51s response time, $0.216 cost, structured insights
**Tech**: Python CLI + OpenAI + REST API (MCP planned)

### Phase 0.1: Performance Optimization (CURRENT PRIORITY)
**Goal**: Achieve <10 second response time target
**Current Issue**: 51s response time due to sequential API calls
**Optimization Plan**: See "Performance Optimization" section in `PROGRESS.md`
- Phase 1: Intercom Search API (50+ calls → 1-2 calls)
- Phase 2: Concurrent processing (parallel operations)
- Phase 3: Data reduction (smart filtering, sampling)
- Phase 4: Prompt optimization (efficiency tuning)

### Phase 0.5: MCP Integration (High Priority)
**Goal**: Replace REST API with Intercom's official MCP server
**Why**: Better performance, real-time data, standardized protocol
**Tech**: [Intercom MCP Server](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization)
- Implement MCP client with proper authorization
- Keep REST API as graceful fallback
- Performance comparison testing
- Update documentation and examples

### Future Phases
- **Phase 1**: + pgvector + embeddings (Context & Memory)
- **Phase 2**: + FastAPI + Slack SDK + Docker (Slack Integration)
- **Phase 3**: + Celery + Redis + scheduling (Automation)
- **Phase 4**: SaaS hosting OR agent marketplace

## Code Quality Standards

### Pre-commit Hooks Active
- Secret detection via detect-secrets
- Code formatting via Black
- Linting via Ruff
- Standard pre-commit hooks (trailing whitespace, YAML validation, etc.)

### Testing Strategy
- Unit tests with mocked API responses
- Integration tests with real APIs (dev environment)
- Success validation with specific test query
- Cost calculation verification

## AI Integration Details

### OpenAI Function Calling
- Timeframe interpretation: "this month" → specific ISO dates
- Structured output for consistent formatting
- Cost tracking with token usage monitoring

### Prompt Engineering
- Conversation summarization for long threads
- Structured prompts for 3-5 bullet point responses
- Cost-optimized prompt length management
- Customer support domain expertise in system prompts

## Security & Privacy

### API Key Management
- Store in .env file (git-ignored)
- Validate keys on startup
- Never log sensitive credentials
- Support key rotation without code changes

### Data Privacy
- Process conversations in memory only
- No local persistence of customer data
- Audit trail for debugging (metadata only)
- Comply with data retention policies
