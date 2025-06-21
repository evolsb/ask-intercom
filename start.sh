#!/bin/bash
# Railway startup script
export PORT=${PORT:-8000}
echo "Starting Ask-Intercom on port $PORT"
exec python -m uvicorn src.web.main:app --host 0.0.0.0 --port $PORT
