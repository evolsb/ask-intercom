# Development Setup

> **Get the development environment running**

## 🚀 Quick Start

### 🐳 Docker Deployment (Recommended)

**Prerequisites**: Docker and Docker Compose

```bash
# Clone repository
git clone https://github.com/evolsb/ask-intercom
cd ask-intercom

# Setup environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables section below)

# One-command deployment
docker-compose up

# Access web interface
open http://localhost:8000
```

**That's it!** The Docker setup handles all dependencies, builds the frontend, and starts the web application.

## 🔧 Environment Variables

Create `.env` file from template:
```bash
cp .env.example .env
```

**Required variables**:
```bash
# Get from: https://developers.intercom.com/building-apps/docs/authentication-types#how-to-get-your-access-token
INTERCOM_ACCESS_TOKEN=your_intercom_token_here

# Get from: https://platform.openai.com/api-keys  
OPENAI_API_KEY=your_openai_key_here
```

**Optional variables** (with defaults):
```bash
OPENAI_MODEL=gpt-4                    # AI model to use
# MAX_CONVERSATIONS=100               # Conversation limit (default: no limit)
# DEBUG=true                         # Show full error tracebacks (for debugging)
ENVIRONMENT=development              # Environment name
```

### 🛠️ Development Setup (Advanced)

**Prerequisites**:
- Python 3.13.3 (available at `/opt/homebrew/bin/python3`)
- Poetry 2.1.3 (available at `~/.local/bin/poetry`)
- Node.js and npm (for frontend)

**Setup**:

1. **Clone and setup backend**:
```bash
cd ask-intercom
~/.local/bin/poetry install
```

2. **Environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Test the CLI**:
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run python -m src.cli "show me issues from the last 24 hours"
```

4. **Setup frontend**:
```bash
cd frontend
npm install
```

### Running the Development Application

**For Docker deployment**: Use `docker-compose up` (see above)

**For development with hot reload**:
```bash
# Backend (in background)
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &

# Frontend (in background)  
cd frontend && npm run dev > /dev/null 2>&1 &
```

**Access the app**: 
- **Docker**: http://localhost:8000
- **Development**: http://localhost:5173

### Development Commands

**Testing**:
```bash
env -i HOME="$HOME" PATH="$PATH" ~/.local/bin/poetry run pytest -v
```

**Code quality**:
```bash
~/.local/bin/poetry run pre-commit run --all-files
```

**Debug logs**:
```bash
tail -f .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl
```

## 🛠️ Project Structure

```
ask-intercom/
├── src/                    # Python backend
│   ├── cli.py             # CLI entry point
│   ├── query_processor.py # Core orchestration
│   ├── intercom_client.py # API integration
│   ├── ai_client.py       # OpenAI integration
│   └── web/               # FastAPI web app
│       └── main.py        # Web server
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   └── store/         # State management
│   └── dist/              # Built assets
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🔧 Important Notes

- **Always use clean environment**: `env -i HOME="$HOME" PATH="$PATH"` for consistency
- **Run servers in background**: Never block terminal with server processes
- **Check logs for debugging**: Use structured logging in `.ask-intercom-analytics/logs/`
- **Environment variables**: Load from `.env` file automatically, don't set in settings files

## 🐛 Troubleshooting

### Common Issues
**Server won't start**: Check if ports 8000/5173 are in use
**API errors**: Verify your `.env` file has valid tokens
**Build fails**: Frontend tests may have issues, but app still works
**Performance**: Response times vary with conversation count and AI processing

### Debug Commands
```bash
# Check server health
curl http://localhost:8000/api/health

# Test API endpoint
curl -X POST http://localhost:8000/api/analyze/stream \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test" \
  -d '{"query": "test", "intercom_token": "...", "openai_key": "..."}'

# Monitor logs in real-time
tail -f .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl

# Check for recent errors
grep -E "(ERROR|error)" .ask-intercom-analytics/logs/backend-*.jsonl | tail -5

# Check server process
ps aux | grep uvicorn
```

### Debug Workflow
1. **Check health endpoint** first - basic connectivity
2. **Check browser DevTools** - Network tab for HTTP errors, Console for JS errors
3. **Check backend logs** - structured JSON logs with full context
4. **Test with curl** - isolate frontend vs backend issues

---

*Last updated: June 20, 2025*
