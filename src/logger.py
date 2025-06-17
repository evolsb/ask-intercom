"""Structured logging configuration for Ask-Intercom."""

import json
import logging
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Thread-local storage for request context
_context = threading.local()


def set_request_context(request_id: str) -> None:
    """Set the current request ID for logging context."""
    _context.request_id = request_id


def get_request_context() -> Optional[str]:
    """Get the current request ID from context."""
    return getattr(_context, "request_id", None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request context if available
        request_id = get_request_context()
        if request_id:
            log_entry["request_id"] = request_id

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        # Add performance metrics if present
        if hasattr(record, "duration"):
            log_entry["duration_seconds"] = record.duration
        if hasattr(record, "tokens_used"):
            log_entry["tokens_used"] = record.tokens_used
        if hasattr(record, "cost_usd"):
            log_entry["cost_usd"] = record.cost_usd
        if hasattr(record, "conversation_count"):
            log_entry["conversation_count"] = record.conversation_count

        # Add error context if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with request ID."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading."""
        # Get request context
        request_id = get_request_context()
        request_prefix = f"[{request_id}] " if request_id else ""

        # Format base message
        formatted = super().format(record)

        return f"{request_prefix}{formatted}"


class MetricsLogger:
    """Logger for performance and cost metrics."""

    def __init__(self, logger_name: str = "ask_intercom.metrics"):
        self.logger = logging.getLogger(logger_name)

    def log_query_performance(
        self,
        query: str,
        duration: float,
        conversation_count: int,
        tokens_used: int,
        cost_usd: float,
        model: str,
    ) -> None:
        """Log query performance metrics."""
        self.logger.info(
            "Query completed",
            extra={
                "query_hash": hash(query) % 10000,  # Privacy-safe query identifier
                "duration_seconds": duration,
                "conversation_count": conversation_count,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "model": model,
                "event_type": "query_completed",
            },
        )

    def log_api_call(
        self,
        api_name: str,
        duration: float,
        success: bool,
        status_code: Optional[int] = None,
    ) -> None:
        """Log API call performance."""
        self.logger.info(
            f"{api_name} API call",
            extra={
                "api_name": api_name,
                "duration_seconds": duration,
                "success": success,
                "status_code": status_code,
                "event_type": "api_call",
            },
        )

    def log_cost_warning(
        self, tokens_used: int, cost_usd: float, threshold: float
    ) -> None:
        """Log cost warnings for expensive queries."""
        self.logger.warning(
            f"High cost query: ${cost_usd:.3f} (threshold: ${threshold:.3f})",
            extra={
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "threshold_usd": threshold,
                "event_type": "cost_warning",
            },
        )


def setup_logging(
    debug: bool = False, structured: bool = True, interactive: bool = False
) -> None:
    """Configure logging for the application."""
    # Determine log level
    level = logging.DEBUG if debug else logging.INFO

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Ensure dev directory exists
    dev_dir = Path(".ask-intercom-dev")
    dev_dir.mkdir(exist_ok=True)

    # Always set up file logging for debugging
    file_handler = RotatingFileHandler(
        dev_dir / "debug.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Always capture debug info to file
    file_handler.setFormatter(StructuredFormatter())

    # Configure root logger with file handler
    root_logger.setLevel(logging.DEBUG)  # Capture everything at root level
    root_logger.addHandler(file_handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    # In interactive mode, only show warnings and errors on console
    console_level = logging.WARNING if interactive else level
    console_handler.setLevel(console_level)

    if structured:
        # Use JSON formatter for structured logging
        console_formatter = StructuredFormatter()
    else:
        # Use human-readable formatter
        if interactive:
            # Minimal formatting for interactive mode
            console_formatter = HumanReadableFormatter("%(levelname)s: %(message)s")
        else:
            console_formatter = HumanReadableFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with consistent configuration."""
    return logging.getLogger(f"ask_intercom.{name}")


def log_with_context(
    logger: logging.Logger, level: int, message: str, **context
) -> None:
    """Log a message with additional context."""
    logger.log(level, message, extra=context)


def append_jsonl(filepath: Path, data: dict) -> None:
    """Append a line to a JSONL file."""
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=str) + "\n")


def log_query_start(request_id: str, query: str) -> None:
    """Log the start of a query to JSONL."""
    data = {
        "id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "query": query,
        "event": "query_start",
    }
    append_jsonl(Path(".ask-intercom-dev/queries.jsonl"), data)


def log_query_result(
    request_id: str,
    success: bool,
    duration: float,
    conversation_count: int = 0,
    tokens: int = 0,
    cost: float = 0.0,
    error: str = None,
) -> None:
    """Log the result of a query to JSONL."""
    data = {
        "id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "success": success,
        "duration": duration,
        "conversation_count": conversation_count,
        "tokens": tokens,
        "cost": cost,
        "error": error,
        "event": "query_result",
    }
    append_jsonl(Path(".ask-intercom-dev/results.jsonl"), data)
