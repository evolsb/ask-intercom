# Ask-Intercom

> **Transform your Intercom conversations into actionable insights**

AI-powered analysis tool with web interface and CLI. Ask natural language questions like "show me issues from last week" and get structured insights with customer details.

## 🚀 Quick Start

### Web Interface (Recommended)
```bash
# Start backend and frontend
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run uvicorn src.web.main:app --port 8000 --reload &
cd frontend && npm run dev &

# Open http://localhost:5173
```

### CLI Usage
```bash
# Setup environment  
~/.local/bin/poetry install
echo "INTERCOM_ACCESS_TOKEN=your_token_here" > .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Ask questions
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "What are the top customer complaints this month?"
```

## ✨ Features

- 🌐 **Web interface** with real-time progress tracking
- 🤖 **AI-powered analysis** using OpenAI GPT-4  
- ⚡ **Natural language queries** ("show me issues from last week")
- 🎯 **Structured insights** with customer details and priorities
- 🔗 **Direct links** to Intercom conversations
- ⚙️ **Optional conversation limits** (user-controlled via Settings)
- 💰 **Cost tracking** and optimization

## 📋 Requirements

- **Python 3.13+** and Poetry
- **Node.js** and npm (for web interface)
- **Intercom access token** 
- **OpenAI API key**

## 📚 Documentation

- **[📖 Getting Started](docs/01-README.md)** - Project overview
- **[⚙️ Setup Guide](docs/02-Setup.md)** - Development environment  
- **[🏗️ Architecture](docs/03-Architecture.md)** - System design
- **[📊 Current Status](docs/04-Current-Status.md)** - What works now
- **[🎯 Next Steps](docs/05-Next-Steps.md)** - Future plans

## 🛠️ Development

See **[CLAUDE.md](CLAUDE.md)** for Claude Code specific guidance and **[docs/](docs/)** for full documentation.
