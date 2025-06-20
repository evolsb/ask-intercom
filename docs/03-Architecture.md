# System Architecture

> **How the components work together**

## 🏗️ High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                          │
├─────────────────────────────────────────────────────────────────┤
│  React Frontend (localhost:5173)                               │
│  • Query input with real-time progress                         │
│  • Structured insight display                                  │  
│  • Optional conversation limits via Settings                   │
│  • Server-Sent Events for live updates                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP/SSE
┌─────────────────▼───────────────────────────────────────────────┐
│                   Web Backend                                  │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Server (localhost:8000)                               │
│  • /api/analyze/stream - Real-time analysis                    │
│  • /api/health - Health checks                                 │
│  • Global exception handling                                   │
│  • Session tracking and logging                                │
└─────────────────┬───────────────────────────────────────────────┘
                  │ Python imports
┌─────────────────▼───────────────────────────────────────────────┐
│                  Core Engine                                   │
├─────────────────────────────────────────────────────────────────┤
│  QueryProcessor                                                 │
│  • Orchestrates full workflow                                  │
│  • Progress callbacks for real-time updates                    │
│  • Simple conversation limits (no smart limits)                │
│  • Error handling and logging                                  │
└─────────┬───────────────────┬───────────────────────────────────┘
          │                   │
          ▼                   ▼
┌─────────────────┐  ┌─────────────────────────────────────────────┐
│ Intercom Client │  │            AI Client                        │
├─────────────────┤  ├─────────────────────────────────────────────┤
│ • REST API      │  │ • Timeframe interpretation                  │
│ • Pagination    │  │ • Structured JSON analysis                  │
│ • Rate limiting │  │ • Fallback to legacy parsing               │
│ • Conversation  │  │ • Cost tracking                             │
│   filtering     │  │ • OpenAI GPT-4 integration                 │
└─────────────────┘  └─────────────────────────────────────────────┘
```

## 🔧 Key Components

### QueryProcessor (`src/query_processor.py`)
**Role**: Main orchestrator  
**Responsibilities**:
- Coordinate timeframe interpretation → conversation fetching → AI analysis
- Provide real-time progress updates via callbacks
- Handle simple conversation limits (user-specified or unlimited)
- Manage costs and performance metrics

### IntercomClient (`src/intercom_client.py`)  
**Role**: Data fetching  
**Responsibilities**:
- Fetch conversations via Search API with pagination
- Handle rate limiting (83 requests/10 seconds)
- Parse and filter conversations
- Support unlimited fetching when no limit specified

### AIClient (`src/ai_client.py`)
**Role**: Intelligence extraction  
**Responsibilities**:
- Parse natural language timeframes ("last 24 hours")
- Generate structured JSON insights from conversations
- Fallback to legacy text parsing if structured fails
- Track token usage and costs

### Web Layer (`src/web/main.py`)
**Role**: User interface backend  
**Responsibilities**:
- Serve React frontend static files
- Provide real-time streaming API via Server-Sent Events
- Handle API key validation and session management
- Global exception handling with structured error responses

## 📊 Data Flow

### 1. Query Processing
```
User Query → Timeframe Parsing → Date Range → Conversation Filters
```

### 2. Data Fetching  
```
Intercom Search API → Paginated Results → Parsed Conversations → Limited Set
```

### 3. AI Analysis
```
Conversations + Query → OpenAI GPT-4 → Structured JSON → Formatted Results
```

### 4. Real-time Updates
```
Progress Callbacks → SSE Stream → Frontend Updates → User Feedback
```

## 🎯 Design Principles

### Simplicity First
- **No smart limits**: User controls conversation limits or sets no limit
- **Direct data flow**: AI → JSON → Frontend (no complex parsing)  
- **Clear error handling**: Structured errors with user-friendly messages

### Performance Optimized
- **Streaming responses**: Real-time progress via Server-Sent Events
- **Efficient pagination**: Batch fetching from Intercom API
- **Cost tracking**: Monitor and optimize OpenAI usage

### User Experience Focused
- **Predictable behavior**: Exact timeframes, no automatic overrides
- **Optional controls**: Settings available but not required
- **Clear feedback**: Progress bars and status messages

## 🔄 Request Lifecycle

1. **User submits query** via React frontend
2. **Frontend sends request** to `/api/analyze/stream`
3. **Backend validates** API keys and request format
4. **QueryProcessor starts** with progress callback setup
5. **Timeframe interpreted** by AI (e.g., "last 24 hours" → date range)
6. **Conversations fetched** from Intercom with pagination
7. **Progress updates** sent via SSE during fetching
8. **AI analysis** generates structured insights
9. **Results streamed** back to frontend in real-time
10. **Frontend displays** insights with customer details

## 📁 File Organization

```
src/
├── cli.py              # Command-line interface
├── query_processor.py  # Main orchestration logic  
├── intercom_client.py  # Intercom API integration
├── ai_client.py        # OpenAI integration
├── models.py           # Data structures
├── config.py           # Configuration management
├── logging.py          # Structured logging
└── web/
    └── main.py         # FastAPI web application

frontend/src/
├── components/         # React UI components
├── store/             # Zustand state management
└── lib/               # Utilities
```

---

*Last updated: June 20, 2025*
