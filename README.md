# Ask-Intercom

Ask natural language questions about your Intercom conversations and get AI-powered insights.

## Quick Start

1. **Setup the environment:**
   ```bash
   ./setup.sh
   ```

2. **Configure your API credentials:**
   Edit `.env` file with your credentials:
   ```bash
   INTERCOM_ACCESS_TOKEN=your_token_here
   OPENAI_API_KEY=your_key_here
   # INTERCOM_APP_ID=your_app_id_here  # Optional - auto-detected
   ```

3. **Run interactively:**
   ```bash
   ./test
   ```

4. **Or run single queries:**
   ```bash
   poetry run python -m src.cli "What are the top customer complaints this month?"
   ```

## Features

- 🤖 AI-powered conversation analysis
- 🔗 Clickable links to Intercom conversations
- ⚡ Fast timeframe interpretation ("this month", "last week", etc.)
- 💰 Cost tracking and optimization
- 🎯 Structured insights with categories and metrics

## Requirements

- Python 3.13+
- Poetry (automatically installed by setup.sh)
- Intercom API access token
- OpenAI API key
- Intercom App ID (optional - auto-detected for conversation links, see [docs/finding-app-id.md](docs/finding-app-id.md))

## Documentation

- **[📚 Full Documentation](docs/index.md)** - Complete documentation hub
- **[🚀 Quick Setup](docs/reference/setup-guide.md)** - Development environment setup
- **[🎯 Current Focus](docs/planning/current-focus.md)** - What's being worked on now
- **[🗺️ Project Roadmap](docs/planning/roadmap.md)** - Strategic overview and timeline

## Development

See **[CLAUDE.md](CLAUDE.md)** for Claude Code specific setup and **[docs/](docs/)** for comprehensive project documentation.
