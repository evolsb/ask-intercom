"""
Enhanced logging system with session management and structured output.
"""

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Context variables for session and request tracking
current_session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
current_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Analytics directory
ANALYTICS_DIR = Path(".ask-intercom-analytics")
LOGS_DIR = ANALYTICS_DIR / "logs"
SESSIONS_DIR = ANALYTICS_DIR / "sessions"
ERRORS_DIR = ANALYTICS_DIR / "errors"
PERFORMANCE_DIR = ANALYTICS_DIR / "performance"

# Ensure directories exist
for directory in [ANALYTICS_DIR, LOGS_DIR, SESSIONS_DIR, ERRORS_DIR, PERFORMANCE_DIR]:
    directory.mkdir(exist_ok=True)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": getattr(record, "service", "backend"),
            "event": getattr(record, "event", "general"),
            "message": record.getMessage(),
        }

        # Add session and request IDs if available
        session_id = current_session_id.get()
        request_id = current_request_id.get()

        if session_id:
            log_entry["session_id"] = session_id
        if request_id:
            log_entry["request_id"] = request_id

        # Add any extra data
        if hasattr(record, "data"):
            log_entry["data"] = record.data

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging() -> logging.Logger:
    """Set up structured logging with file rotation."""
    logger = logging.getLogger("ask_intercom")
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # File handlers for different log types
    today = datetime.now().strftime("%Y-%m-%d")

    # Main application log
    main_handler = logging.FileHandler(LOGS_DIR / f"backend-{today}.jsonl")
    main_handler.setFormatter(StructuredFormatter())
    logger.addHandler(main_handler)

    # Error-specific log
    error_handler = logging.FileHandler(LOGS_DIR / f"errors-{today}.jsonl")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    logger.addHandler(error_handler)

    return logger


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return f"sess_{uuid.uuid4().hex[:12]}"


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def set_session_context(session_id: str, request_id: Optional[str] = None):
    """Set session and request context for logging."""
    current_session_id.set(session_id)
    if request_id:
        current_request_id.set(request_id)


def clear_session_context():
    """Clear session and request context."""
    current_session_id.set(None)
    current_request_id.set(None)


class SessionLogger:
    """Enhanced logger with session tracking capabilities."""

    def __init__(self):
        self.logger = setup_logging()

    def info(
        self,
        message: str,
        event: str = "general",
        service: str = "backend",
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log info message with context."""
        extra = {"event": event, "service": service}
        if data:
            extra["data"] = data
        self.logger.info(message, extra=extra)

    def error(
        self,
        message: str,
        event: str = "error",
        service: str = "backend",
        data: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """Log error message with context."""
        extra = {"event": event, "service": service}
        if data:
            extra["data"] = data
        self.logger.error(message, extra=extra, exc_info=exc_info)

    def warning(
        self,
        message: str,
        event: str = "warning",
        service: str = "backend",
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log warning message with context."""
        extra = {"event": event, "service": service}
        if data:
            extra["data"] = data
        self.logger.warning(message, extra=extra)

    def log_query_start(self, query: str, config_data: Dict[str, Any]):
        """Log the start of a query processing."""
        self.info(
            f"Query processing started: {query[:100]}{'...' if len(query) > 100 else ''}",
            event="query_start",
            data={
                "query": query,
                "max_conversations": config_data.get("max_conversations"),
                "start_time": datetime.utcnow().isoformat(),
            },
        )

    def log_query_complete(
        self, query: str, result_data: Dict[str, Any], duration_ms: int
    ):
        """Log the completion of a query processing."""
        self.info(
            f"Query processing completed in {duration_ms}ms",
            event="query_complete",
            data={
                "query": query,
                "duration_ms": duration_ms,
                "conversation_count": result_data.get("conversation_count"),
                "insights_count": len(result_data.get("insights", [])),
                "cost_usd": result_data.get("cost"),
                "tokens_used": result_data.get("tokens_used"),
            },
        )

    def log_api_error(
        self, service: str, error_type: str, message: str, context: Dict[str, Any]
    ):
        """Log API-related errors with full context."""
        self.error(
            f"{service} API error: {message}",
            event="api_error",
            service=service,
            data={
                "error_type": error_type,
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            },
            exc_info=True,
        )


class SessionManager:
    """Manages user sessions and tracks interaction history."""

    def __init__(self):
        self.logger = SessionLogger()

    def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = generate_session_id()
        session_data = {
            "session_id": session_id,
            "start_time": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "queries": [],
            "errors": [],
            "performance": [],
        }

        # Save session file
        session_file = SESSIONS_DIR / f"{session_id}.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        self.logger.info(f"New session created: {session_id}", event="session_start")
        return session_id

    def update_session(self, session_id: str, update_data: Dict[str, Any]):
        """Update session with new activity data."""
        session_file = SESSIONS_DIR / f"{session_id}.json"

        if session_file.exists():
            with open(session_file, "r") as f:
                session_data = json.load(f)

            session_data["last_activity"] = datetime.utcnow().isoformat()
            session_data.update(update_data)

            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

    def log_session_query(
        self, session_id: str, query: str, result: Dict[str, Any], duration_ms: int
    ):
        """Log a query within a session."""
        query_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "result": result,
            "duration_ms": duration_ms,
        }

        session_file = SESSIONS_DIR / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, "r") as f:
                session_data = json.load(f)

            session_data["queries"].append(query_data)
            session_data["last_activity"] = datetime.utcnow().isoformat()

            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)


def cleanup_old_logs(days: int = 30):
    """Clean up log files older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days)

    for log_dir in [LOGS_DIR, SESSIONS_DIR, ERRORS_DIR, PERFORMANCE_DIR]:
        for log_file in log_dir.glob("*.json*"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                log_file.unlink()


# Global instances
session_logger = SessionLogger()
session_manager = SessionManager()
