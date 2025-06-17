# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- **Dependencies**: `~/.local/bin/poetry install` (installs from pyproject.toml)

### Environment Variables
```bash
# Required in .env file
INTERCOM_ACCESS_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here

# Optional with defaults
OPENAI_MODEL=gpt-4
MAX_CONVERSATIONS=50
DEBUG=false
```

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

### Current: Phase 0 (CLI Prototype)
**Goal**: Prove AI + MCP integration works
**Tech**: Python CLI + OpenAI + REST API (MCP planned)

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
