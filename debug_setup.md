# Debugging Best Practices for Full-Stack Web Development

## 1. Structured Error Handling

### Backend (FastAPI)
- **Global exception handlers** for unhandled errors
- **Request/response middleware** for comprehensive logging
- **Validation error handlers** for Pydantic validation failures
- **API error classes** with structured error responses

### Frontend (React)
- **Error boundaries** to catch React component errors
- **Global error handler** for fetch/network errors  
- **Console logging** with structured error objects
- **User-friendly error messages** with technical details in console

## 2. Comprehensive Logging

### Backend
```python
# Every endpoint should log:
# - Request start/end with duration
# - Input parameters (sanitized)
# - Each major step within the function
# - Validation failures with details
# - Exception stack traces
```

### Frontend
```javascript
// Every API call should log:
// - Request details (URL, method, headers)
// - Response status and headers
// - Response body (first 200 chars if large)
// - Parse errors with original text
```

## 3. Development Tools

### Backend
- **Uvicorn with reload** for hot-reloading
- **Structured JSON logging** for easier parsing
- **Health check endpoints** for quick verification
- **Debug mode** with detailed error responses

### Frontend  
- **Source maps** enabled in development
- **React DevTools** for component debugging
- **Network tab monitoring** for API calls
- **Console error handling** that preserves stack traces

## 4. Error Detection Workflow

1. **Start with health checks** - verify basic connectivity
2. **Test individual endpoints** with curl before UI testing
3. **Check browser DevTools Network tab** for HTTP status codes
4. **Check browser Console** for JavaScript errors
5. **Check backend logs** for server-side errors
6. **Use structured error IDs** to correlate frontend/backend errors

## 5. Quick Debug Commands

```bash
# Check server health
curl http://localhost:8000/api/health

# Test endpoint with curl
curl -v -X POST http://localhost:8000/api/endpoint -H "Content-Type: application/json" -d '{}'

# Check recent logs
tail -f .ask-intercom-analytics/logs/backend-$(date +%Y-%m-%d).jsonl

# Check for errors
grep -E "(ERROR|error|exception)" .ask-intercom-analytics/logs/backend-*.jsonl | tail -10
```

## 6. What We Missed This Time

- ❌ **No global exception handler** - Pydantic validation errors weren't caught
- ❌ **No request validation logging** - Config creation failures were silent
- ❌ **No frontend error boundary** - JSON parse errors weren't handled gracefully  
- ❌ **No structured error correlation** - Couldn't easily match frontend/backend errors

## 7. Immediate Improvements Needed

1. Add FastAPI global exception handler for ValidationError
2. Add request/response logging middleware
3. Add frontend error boundary component
4. Add error correlation IDs
5. Add development debugging endpoint with server state
