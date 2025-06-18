# CLAUDE.md

This file provides crucial guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start for New Claude Sessions

**⚠️ MANDATORY FIRST STEP - DO NOT SKIP:**
**Claude MUST read project documentation BEFORE any coding work:**
```bash
# REQUIRED: Read these files first, in order:
# 1. docs/index.md (project overview)
# 2. docs/planning/current-focus.md (current priorities)
# 3. Relevant docs/web/ or docs/mcp/ files based on focus
```

**⚠️ IF YOU START CODING WITHOUT READING DOCS FIRST, YOU ARE DOING IT WRONG!**

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

Ask-Intercom is an AI-powered tool that turns raw Intercom conversations into actionable product, support, and roadmap insights. The project follows a risk-first development approach.

**Current Status:** Check `docs/planning/current-focus.md` for latest phase and priorities

## Core Architecture

### Key Components
- **CLI Interface** (`src/cli.py`): Main entry point
- **Query Processor** (`src/query_processor.py`): Orchestrates workflows
- **Intercom Client** (`src/intercom_client.py`): API integration
- **AI Client** (`src/ai_client.py`): OpenAI integration
- **Web Interface** (`src/web/main.py`, `frontend/`): FastAPI + React

### Design Principles
- **Risk-first development**: Tackle hardest problems early
- **Graceful degradation**: Multiple fallback strategies
- **Cost optimization**: Token tracking and prompt engineering
- **Structured logging**: Full observability for debugging

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
- **Debug logs**: `.ask-intercom-analytics/logs/` (structured JSON, daily rotation)
- **Session logs**: `.ask-intercom-analytics/sessions/` (user session history)
- **Error logs**: `.ask-intercom-analytics/logs/errors-YYYY-MM-DD.jsonl` (error tracking)
- **View recent logs**: `tail -50 .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl`
- **Search logs**: `grep "ERROR\|error" .ask-intercom-analytics/logs/*.jsonl`
- **Debug mode**: Add `--debug` flag to CLI commands for verbose console output

**⚠️ IMPORTANT SERVER MANAGEMENT:**
- **ALWAYS run servers in background:** `command > /dev/null 2>&1 &`
- **Then tail logs for debugging:** `tail -f .ask-intercom-analytics/logs/backend-*.jsonl`
- **Never run servers in foreground** - Claude gets stuck waiting
- **Use log analysis tools:** Claude can analyze logs with structured queries

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

## Key Technical Decisions

### Error Handling Strategy
- **API failures**: Graceful fallbacks and clear error messages
- **Rate limiting**: Respect Intercom limits (83 requests/10 seconds)
- **Cost control**: Optimize prompts, warn on expensive queries

### Data Flow
1. Parse natural language query for time context
2. Convert to specific date ranges
3. Fetch conversations via API
4. Analyze with AI and return structured results

## Development Strategy

**Current development follows parallel tracks - see `docs/planning/current-focus.md` for details**

### Key Success Criteria
- CLI answers "What are the top customer complaints this month?" correctly
- Response time < 10 seconds consistently  
- Cost per query < $0.50
- Graceful error handling for API failures
- Clear, actionable output format

## Code Quality Standards

### Pre-commit Hooks
- `detect-secrets` for security
- `black` and `ruff` for code formatting
- Run: `~/.local/bin/poetry run pre-commit run --all-files`

### Security
- API keys in `.env` file only
- No customer data persistence
- Process conversations in memory only

## 📋 Documentation Maintenance (CRITICAL - NEVER SKIP)

**🚨 CLAUDE MUST FOLLOW THIS WORKFLOW EVERY SINGLE SESSION 🚨**

### ⚠️ BEFORE ANY CODING (MANDATORY):
1. **Read current state**: `docs/index.md` → `docs/planning/current-focus.md`
2. **Choose track**: MCP integration OR Web deployment  
3. **Check tasks**: Read relevant `tasks.md` and `progress.md` files
4. **STOP AND CONFIRM**: You understand the current project state

### During Work (REQUIRED):
5. **Update progress**: Mark tasks in progress, add new discoveries
6. **Document decisions**: Add to `docs/reference/decisions.md` if architectural

### ⚠️ AFTER COMPLETING WORK (MANDATORY):
7. **Mark completion**: Update task status and add results
8. **Update focus**: Modify `docs/planning/current-focus.md` with next steps  
9. **Log important findings**: Update relevant progress files
10. **CONFIRM DOCS UPDATED**: Explicitly state you've updated documentation

**🚨 FAILURE TO UPDATE DOCS IS A CRITICAL ERROR 🚨**

**The documentation structure in `docs/` is the single source of truth for project state.**

### Enforcement Reminders:
- **If you code without reading docs first → YOU FAILED**
- **If you finish work without updating docs → YOU FAILED**  
- **Documentation updates are NOT optional → THEY ARE MANDATORY**
