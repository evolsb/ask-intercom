# Logging & Debugging Infrastructure Plan

> **Critical**: Enable instant debugging and quality control for Ask-Intercom

## Problem Statement

User experiencing errors in web app that can't be easily diagnosed:
- No visibility into backend/frontend logs
- Generic error messages provide no actionable information
- No session correlation between user actions and system behavior
- No learning from user interactions for quality improvement

## Solution Architecture

### 1. Session Management & Correlation

```typescript
interface Session {
  sessionId: string;           // UUID for user session
  requestId: string;           // UUID per request
  userId?: string;             // Future: user identification
  startTime: Date;
  lastActivity: Date;
  queries: QueryLog[];
  errors: ErrorLog[];
  performance: PerformanceLog[];
}
```

**Implementation**:
- Generate session ID on first page load, persist in localStorage
- Create request ID for each API call
- Track session duration and query patterns
- Store locally for immediate access, sync for learning

### 2. Structured Logging System

```json
{
  "timestamp": "2025-01-15T14:30:22.123Z",
  "level": "INFO|WARN|ERROR",
  "sessionId": "sess_abc123",
  "requestId": "req_def456",
  "service": "frontend|backend|intercom|openai",
  "event": "query_start|query_complete|error",
  "data": {
    "query": "...",
    "response_time_ms": 5432,
    "tokens_used": 1500,
    "cost_usd": 0.25,
    "error_type": "api_key_invalid",
    "stack_trace": "..."
  }
}
```

**Log Files Structure**:
```
.ask-intercom-analytics/
├── logs/
│   ├── frontend-2025-01-15.jsonl
│   ├── backend-2025-01-15.jsonl
│   ├── errors-2025-01-15.jsonl
│   └── performance-2025-01-15.jsonl
├── sessions/
│   ├── session-abc123.json
│   └── session-def456.json
└── analysis/
    ├── daily-summary-2025-01-15.json
    └── error-patterns.json
```

### 3. Claude Integration Tools

**Commands for instant debugging**:
- `show me errors from the last hour`
- `debug session abc123`
- `what's the performance trend today?`
- `analyze error patterns`

**Implementation**:
- Log analysis functions that Claude can call
- Session replay with full context
- Automated error categorization
- Performance trend analysis

### 4. Environment Validation & Health Checks

**Startup Validation**:
```python
@app.on_event("startup")
async def validate_environment():
    """Validate all required environment variables and connectivity."""
    results = {
        "env_vars": validate_env_vars(),
        "intercom_connectivity": test_intercom_connection(),
        "openai_connectivity": test_openai_connection(),
        "file_permissions": check_log_directory(),
    }
    
    if not all(results.values()):
        logger.error("Environment validation failed", extra={"results": results})
        raise RuntimeError("Invalid environment configuration")
```

**Health Check Endpoint** (`/api/debug`):
```json
{
  "status": "healthy|degraded|unhealthy",
  "environment": {
    "intercom_token": "present|missing|invalid",
    "openai_key": "present|missing|invalid",
    "log_directory": "writable|readonly|missing"
  },
  "connectivity": {
    "intercom_api": "reachable|unreachable|unauthorized",
    "openai_api": "reachable|unreachable|unauthorized"
  },
  "performance": {
    "last_query_time_ms": 5432,
    "avg_response_time_24h": 4123,
    "error_rate_24h": 0.02
  }
}
```

### 5. Enhanced Error Handling

**Backend Error Categories**:
- `environment_error`: Missing/invalid API keys
- `connectivity_error`: Can't reach external APIs
- `rate_limit_error`: API quotas exceeded
- `validation_error`: Invalid user input
- `processing_error`: Internal logic failures

**Frontend Error Display**:
```typescript
interface ErrorDisplay {
  sessionId: string;
  requestId: string;
  category: ErrorCategory;
  message: string;
  userActionRequired: string;
  retryable: boolean;
  supportInfo?: {
    sessionId: string;
    timestamp: string;
    errorCode: string;
  };
}
```

### 6. Local Analytics Storage

**Session Storage**:
- Full query/response history for learning
- User interaction patterns
- Performance metrics per session
- Error occurrence and resolution

**Quality Control Metrics**:
- Success rate (% queries that complete)
- User satisfaction inference (session length, repeat usage)
- Performance trends (response times)
- Error patterns and frequencies

**Privacy & Retention**:
- Hash user data for privacy
- 30-day automatic deletion
- Separate PII from analytics data
- Future: Federated learning preparation

## Implementation Priority

### Phase 1: Critical Debugging (Immediate)
1. Session ID generation and persistence
2. Structured JSON logging with correlation
3. Environment validation on startup
4. Health check endpoint with diagnostics
5. Enhanced error messages in frontend

### Phase 2: Claude Integration (This Session)
1. Log analysis functions for Claude
2. Real-time log tailing
3. Session replay functionality
4. Error pattern detection

### Phase 3: Analytics Foundation (Next Session)
1. Local session storage system
2. Performance trend analysis
3. Quality control metrics
4. Automated insights generation

## Success Criteria

**Immediate (Phase 1)**:
- User reports error → Claude can see logs and diagnose in <30 seconds
- Clear error messages tell user exactly what's wrong
- Health check endpoint shows system status

**Short-term (Phase 2)**:
- Claude can analyze patterns: "5 users hit API key errors today"
- Session replay allows debugging without user description
- Automated error categorization and trending

**Long-term (Phase 3)**:
- Quality metrics show improvement over time
- Learning from user sessions improves performance
- Foundation ready for SaaS federated learning

## Technical Implementation

### Backend Changes
```python
# New middleware for session tracking
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.headers.get("X-Session-ID")
    request_id = str(uuid.uuid4())
    
    with logger.contextualize(session_id=session_id, request_id=request_id):
        response = await call_next(request)
        return response

# Enhanced error handling
class APIError(Exception):
    def __init__(self, category: str, message: str, user_action: str, retryable: bool):
        self.category = category
        self.message = message
        self.user_action = user_action
        self.retryable = retryable
```

### Frontend Changes
```typescript
// Session management
const sessionManager = {
  getSessionId: () => localStorage.getItem('sessionId') || generateSessionId(),
  getRequestId: () => `req_${Date.now()}_${Math.random()}`,
  
  logError: (error: APIError) => {
    const errorLog = {
      sessionId: sessionManager.getSessionId(),
      timestamp: new Date().toISOString(),
      error: error,
    };
    
    // Store locally and send to backend
    localStorage.setItem(`error_${Date.now()}`, JSON.stringify(errorLog));
    sendErrorToBackend(errorLog);
  }
};

// Enhanced error display
const ErrorMessage = ({ error }: { error: APIError }) => (
  <div className="error-container">
    <h3>{error.category}: {error.message}</h3>
    <p>{error.userAction}</p>
    {error.retryable && <button onClick={retry}>Try Again</button>}
    <details>
      <summary>Support Information</summary>
      <p>Session: {sessionManager.getSessionId()}</p>
      <p>Time: {new Date().toISOString()}</p>
    </details>
  </div>
);
```

## Future Enhancements

### SaaS Preparation
- Multi-tenant session isolation
- Aggregated analytics across users
- A/B testing framework for prompt improvements
- Real-time monitoring dashboards

### Federated Learning
- Privacy-preserving analytics aggregation
- Cross-user pattern detection without data sharing
- Distributed model improvements
- Quality insights at scale

---

*This plan addresses the immediate debugging crisis while building foundation for long-term learning and quality control.*
