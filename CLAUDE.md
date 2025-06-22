# CLAUDE.md

This file provides essential guidance for Claude Code when working with this repository.

## 🚀 Quick Start for New Claude Sessions

**⚠️ MANDATORY FIRST STEP:**
**Read current documentation BEFORE any coding work:**
```bash
# REQUIRED: Read these files first, in order:
# 1. docs/04-Current-Status.md (what works now, recent changes)
# 2. docs/05-Next-Steps.md (planned improvements and priorities)
```

**Test the system:**
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "show me issues from the last 24 hours"
```

**Run tests:**
```bash  
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run pytest -v
```

**Debug logs:**
```bash
tail -f .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl
```

## Project Overview

Ask-Intercom is an AI-powered tool that turns Intercom conversations into actionable product insights with:
- **MCP Architecture**: Universal adapter supporting multiple backends (FastIntercom, official, local, REST)
- **Web Interface**: React frontend with real-time progress tracking
- **CLI Interface**: Python CLI for direct queries
- **Structured Logging**: Full observability for debugging

## Development Environment

### Dependencies & Commands
- **Python**: 3.13+ with Poetry at `~/.local/bin/poetry`
- **Testing**: `~/.local/bin/poetry run pytest -v`
- **CLI**: `~/.local/bin/poetry run python -m src.cli "your query"`
- **Web**: `uvicorn src.web.main:app --port 8000 --reload`

### Critical Runtime Environment
**ALWAYS use clean environment to avoid variable conflicts:**
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "query"
```

**Environment Variables** are loaded from `.env` file automatically.

### Key File Locations
- **Main CLI**: `src/cli.py` - Entry point with argparse and Rich formatting
- **MCP Integration**: `src/mcp/universal_adapter.py` - Universal MCP adapter
- **Web API**: `src/web/main.py` - FastAPI backend with SSE support
- **Frontend**: `frontend/` - React/TypeScript UI
- **Configuration**: `src/config.py` - Settings and validation
- **Environment Config**: `.env` - Contains API keys

### MCP Configuration
```bash
# Enable MCP functionality
ENABLE_MCP=true
MCP_BACKEND=fastintercom|official|local|auto

# Fallback chain: official → fastintercom → local → REST
```

### Debugging & Logs

#### Local Development
- **Debug logs**: `.ask-intercom-analytics/logs/backend-YYYY-MM-DD.jsonl`
- **Session logs**: `.ask-intercom-analytics/sessions/` (user session history)
- **View recent logs**: `tail -50 .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl`
- **Debug endpoints**: `GET http://localhost:8000/api/debug`

### Development Safety Checks
- **Before starting development**: `./scripts/dev-check.sh` 
- **Checks for**: Stale servers, uncommitted changes, unsafe CostInfo usage, port conflicts
- **Prevents**: Runtime errors from old code, parameter mismatches, server conflicts

### Pre-commit Workflow
- **Run hooks before committing**: `~/.local/bin/poetry run pre-commit run --all-files`
- **Critical hooks**: `detect-secrets` (security), `black`/`ruff` (code quality)

### Testing & Quality Assurance
- **Unit tests**: `~/.local/bin/poetry run pytest tests/unit/`
- **Integration tests**: `~/.local/bin/poetry run pytest tests/integration/`
- **MCP tests**: `~/.local/bin/poetry run pytest tests/integration/test_mcp_only_architecture.py`

## Key Technical Decisions

### MCP-First Architecture
- **Universal Adapter**: Supports multiple MCP backends with graceful fallbacks
- **Performance**: FastIntercom MCP provides 400x speedup for cached queries
- **Reliability**: Automatic fallback chain ensures queries always succeed

### Error Handling Strategy
- **API failures**: Graceful fallbacks through MCP → FastIntercom → Local → REST
- **Rate limiting**: Respect Intercom limits with built-in retry logic
- **Cost control**: Optimize prompts, warn on expensive queries

## Security & Best Practices
- **API keys**: Store in `.env` file only, never commit
- **No customer data persistence**: Process conversations in memory only
- **Session management**: Full audit trail for debugging
- **Input validation**: Comprehensive parameter validation with CostInfo helpers

## Code References

When referencing specific functions include the pattern `file_path:line_number` for easy navigation.

Example: Clients are validated in `src/config.py:45-67`.
