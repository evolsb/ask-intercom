"""Structured logging configuration for Ask-Intercom."""

import json
import logging
import sys
from datetime import datetime
from typing import Optional


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


def setup_logging(debug: bool = False, structured: bool = True) -> None:
    """Configure logging for the application."""
    # Determine log level
    level = logging.DEBUG if debug else logging.INFO

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if structured:
        # Use JSON formatter for structured logging
        formatter = StructuredFormatter()
    else:
        # Use simple formatter for human-readable logs
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(level)
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
