# Development Setup Guide

> **Quick reference for getting the development environment running**

## 🚀 Quick Start

### Prerequisites
```bash
# Ensure you have the right versions
/opt/homebrew/bin/python3 --version  # Should be 3.13.3
~/.local/bin/poetry --version         # Should be 2.1.3
```

### Environment Setup
```bash
# Clone and enter the repo
git clone https://github.com/evolsb/ask-intercom.git
cd ask-intercom

# Install dependencies
~/.local/bin/poetry install

# Copy environment template
cp .env.example .env
# Edit .env with your API keys:
# INTERCOM_ACCESS_TOKEN=your_token_here
# OPENAI_API_KEY=your_key_here
```

### Test Installation
```bash
# Test the CLI with clean environment
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "what are the top customer complaints this month?"

# Run tests
~/.local/bin/poetry run pytest -v

# Run integration tests
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python tests/integration/test_timeframe_consistency.py
```

## 🔧 Development Commands

### Common CLI Usage
```bash
# Basic query
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "your query here"

# Debug mode
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli --debug "your query"

# Interactive mode
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli --interactive
```

### Testing & Quality
```bash
# Run all tests
~/.local/bin/poetry run pytest -v

# Run specific test file
~/.local/bin/poetry run pytest tests/unit/test_models.py -v

# Pre-commit quality checks
~/.local/bin/poetry run pre-commit run --all-files

# Quick file fixes
~/.local/bin/poetry run pre-commit run --files src/specific_file.py
```

### Debugging & Logs
```bash
# View recent debug logs
tail -50 .ask-intercom-dev/debug.log

# Watch logs in real-time
tail -f .ask-intercom-dev/debug.log

# Search for errors
grep "ERROR\|error" .ask-intercom-dev/debug.log

# See query logs
cat .ask-intercom-dev/queries.jsonl
```

## 📁 Project Structure

```
ask-intercom/
├── src/                     # Main application code
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── query_processor.py  # Core orchestration
│   ├── intercom_client.py  # API client
│   ├── ai_client.py        # OpenAI integration
│   └── models.py           # Data models
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Test configuration
├── docs/                    # Documentation
└── .ask-intercom-dev/      # Debug logs and data
```

## 🌐 Git Workflow

### Branch Strategy for Parallel Development
```bash
# Main development branch
git checkout main

# MCP Integration track
git checkout -b feature/mcp-integration

# Web deployment track  
git checkout -b feature/web-deployment

# Switch between tracks based on energy/mood
git checkout feature/mcp-integration    # For backend/architecture work
git checkout feature/web-deployment     # For frontend/UI work
```

### Common Git Operations
```bash
# Commit with pre-commit hooks
git add -A
git commit -m "descriptive message"

# If pre-commit hooks make changes
git add -A && git commit -m "same message"

# Push branch
git push -u origin feature/branch-name

# Sync with main
git checkout main
git pull
git checkout feature/branch-name
git rebase main
```

## 🔑 Environment Variables

Required in `.env` file:
```bash
# Required
INTERCOM_ACCESS_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here

# Optional with defaults
INTERCOM_APP_ID=your_app_id_here  # Auto-fetched if not provided
OPENAI_MODEL=gpt-4
MAX_CONVERSATIONS=50
DEBUG=false

# Future MCP integration
ENABLE_MCP=false
MCP_SERVER_URL=https://mcp.intercom.com/sse
MCP_OAUTH_TOKEN=
```

## 🚨 Common Issues

### Poetry Issues
```bash
# If poetry command not found
export PATH="$HOME/.local/bin:$PATH"

# If dependencies fail to install
~/.local/bin/poetry lock --no-update
~/.local/bin/poetry install
```

### Environment Issues
```bash
# Always use clean environment for CLI
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli

# If .env variables aren't loading
# Check that .env file exists and has correct format
# Don't set variables in .claude/settings.json (they override .env)
```

### API Issues
```bash
# Test Intercom connection
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -c "
from src.config import Config
from src.intercom_client import IntercomClient
config = Config.from_env()
client = IntercomClient(config.intercom_access_token)
print('Connection test passed')
"

# Check API key validity
# Make sure INTERCOM_ACCESS_TOKEN has proper permissions
# Make sure OPENAI_API_KEY has credits available
```

---

**For more detailed guidance, see the main documentation at [`docs/index.md`](../index.md)**
