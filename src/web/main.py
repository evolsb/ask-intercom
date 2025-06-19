"""
FastAPI web application wrapping the Ask-Intercom CLI functionality.
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from time import time
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import our existing CLI components
from ..ai_client import AIClient
from ..config import Config
from ..health import HealthStatus, health_checker
from ..logging import (
    generate_request_id,
    generate_session_id,
    session_logger,
    session_manager,
    set_session_context,
)
from ..query_processor import QueryProcessor

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Ask-Intercom API",
    description="Transform Intercom conversations into actionable insights",
    version="0.1.0",
)


# Session tracking middleware
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Add session and request tracking to all requests."""
    # Get or create session ID
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = generate_session_id()

    # Generate request ID
    request_id = generate_request_id()

    # Set logging context
    set_session_context(session_id, request_id)

    # Log request start
    session_logger.info(
        f"{request.method} {request.url.path}",
        event="request_start",
        data={
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("user-agent"),
        },
    )

    start_time = time()
    response = await call_next(request)
    duration_ms = int((time() - start_time) * 1000)

    # Add session ID to response headers
    response.headers["X-Session-ID"] = session_id
    response.headers["X-Request-ID"] = request_id

    # Log request completion
    session_logger.info(
        f"{request.method} {request.url.path} completed in {duration_ms}ms",
        event="request_complete",
        data={
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    return response


# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Environment validation on startup
@app.on_event("startup")
async def validate_environment():
    """Validate environment configuration on startup."""
    session_logger.info("Starting Ask-Intercom API", event="startup")

    # Validate environment
    health_status = await health_checker.get_health_status()

    if not health_status.environment.valid:
        session_logger.error(
            "Environment validation failed",
            event="startup_error",
            data={"environment_status": health_status.environment.dict()},
        )
        # Don't fail startup, but log the issues

    session_logger.info(
        f"API started with status: {health_status.status}",
        event="startup_complete",
        data={"health_status": health_status.status},
    )


# Store frontend directory for later mounting
frontend_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"


def get_smart_max_conversations(
    query: str, requested_max: int | None = None
) -> tuple[int, str | None]:
    """Calculate smart max_conversations based on query timeframe.

    Returns:
        tuple: (max_conversations, adjustment_message)
    """
    # If user explicitly requested a high limit, respect it but cap at 500
    if requested_max is not None and requested_max > 100:
        if requested_max > 500:
            return (
                500,
                f"Capped user-requested limit from {requested_max} to 500 conversations",
            )
        return requested_max, None

    # Ignore small hardcoded limits (50, 100) and use smart limits instead
    # This handles legacy frontend requests that hardcode max_conversations: 50

    # Use smart limits based on timeframe
    try:
        ai_client = AIClient("dummy", "gpt-4")  # Just for timeframe parsing
        timeframe = ai_client._parse_timeframe_deterministic(query)

        duration_days = (
            (timeframe.end_date - timeframe.start_date).days
            if timeframe.start_date and timeframe.end_date
            else 30
        )

        # Smart limits based on timeframe
        if duration_days <= 1:  # Today/yesterday
            return (
                100,
                f"Using 100 conversations for {timeframe.description} (short timeframe)",
            )
        elif duration_days <= 7:  # This/last week
            return (
                300,
                f"Using 300 conversations for {timeframe.description} (weekly timeframe)",
            )
        elif duration_days <= 30:  # This/last month
            return (
                500,
                f"Using 500 conversations for {timeframe.description} (monthly timeframe)",
            )
        else:  # Longer periods
            return (
                500,
                f"Using 500 conversations for {timeframe.description} (extended timeframe)",
            )
    except Exception:
        # Fallback if timeframe parsing fails
        return 100, "Using 100 conversations (fallback - could not determine timeframe)"


class HealthResponse(BaseModel):
    status: str
    message: str


class AnalysisRequest(BaseModel):
    query: str
    intercom_token: str | None = None
    openai_key: str | None = None
    max_conversations: int | None = None  # If None, use smart limits


class AnalysisResponse(BaseModel):
    insights: list[str]
    summary: str  # Full analysis with URLs
    cost: float
    response_time_ms: int
    conversation_count: int
    session_id: str
    request_id: str


class StructuredInsightCustomer(BaseModel):
    email: str
    conversation_id: str
    intercom_url: str
    issue_summary: str


class StructuredInsightImpact(BaseModel):
    customer_count: int
    percentage: float
    severity: str


class StructuredInsight(BaseModel):
    id: str
    category: str
    title: str
    description: str
    impact: StructuredInsightImpact
    customers: list[StructuredInsightCustomer]
    priority_score: int
    recommendation: str


class StructuredAnalysisSummary(BaseModel):
    total_conversations: int
    total_messages: int
    analysis_timestamp: str


class StructuredAnalysisResponse(BaseModel):
    insights: list[StructuredInsight]
    summary: StructuredAnalysisSummary
    cost: float
    response_time_ms: int
    session_id: str
    request_id: str


class ErrorResponse(BaseModel):
    error_category: str
    message: str
    user_action: str
    retryable: bool
    session_id: str
    request_id: str
    timestamp: str


class ValidationRequest(BaseModel):
    intercom_token: str
    openai_key: str


class ValidationResponse(BaseModel):
    status: str  # "valid", "invalid", "error"
    environment: dict
    connectivity: dict
    errors: list[str] = []


class APIError(HTTPException):
    def __init__(
        self,
        category: str,
        message: str,
        user_action: str,
        retryable: bool = False,
        status_code: int = 400,
    ):
        self.category = category
        self.user_action = user_action
        self.retryable = retryable
        super().__init__(status_code=status_code, detail=message)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(status="healthy", message="Ask-Intercom API is running")


@app.get("/api/debug", response_model=HealthStatus)
async def debug_status():
    """Comprehensive diagnostic endpoint for debugging."""
    try:
        health_status = await health_checker.get_health_status()
        return health_status
    except Exception as e:
        session_logger.error(
            f"Debug endpoint failed: {str(e)}", event="debug_error", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Health check failed") from e


@app.post("/api/validate", response_model=ValidationResponse)
async def validate_api_keys(request: ValidationRequest, http_request: Request):
    """Validate API keys and test connectivity."""
    # Extract headers but don't use them yet (planned for future logging enhancement)
    _ = http_request.headers.get("X-Session-ID", "unknown")  # noqa: F841
    _ = http_request.headers.get("X-Request-ID", "unknown")  # noqa: F841

    try:
        # Log validation attempt
        session_logger.info(
            "API key validation requested",
            event="validation_start",
            data={
                "has_intercom_token": bool(request.intercom_token),
                "has_openai_key": bool(request.openai_key),
            },
        )

        # Create temporary health checker with provided keys
        from ..health import EnvironmentValidator

        validator = EnvironmentValidator()

        # Test key formats
        errors = []
        environment = {}

        # Validate Intercom token format
        if not request.intercom_token:
            errors.append("Intercom token is missing")
            environment["intercom_token"] = "missing"
        elif not validator._is_valid_intercom_token(request.intercom_token):
            errors.append("Intercom token has invalid format")
            environment["intercom_token"] = "invalid_format"
        else:
            environment["intercom_token"] = "present"

        # Validate OpenAI key format
        if not request.openai_key:
            errors.append("OpenAI API key is missing")
            environment["openai_key"] = "missing"
        elif not validator._is_valid_openai_key(request.openai_key):
            errors.append("OpenAI API key has invalid format (should start with 'sk-')")
            environment["openai_key"] = "invalid_format"
        else:
            environment["openai_key"] = "present"

        # If format validation fails, return early
        if errors:
            return ValidationResponse(
                status="invalid",
                environment=environment,
                connectivity={"intercom_api": "not_tested", "openai_api": "not_tested"},
                errors=errors,
            )

        # Test actual connectivity by temporarily setting environment variables
        old_intercom = os.environ.get("INTERCOM_ACCESS_TOKEN")
        old_openai = os.environ.get("OPENAI_API_KEY")

        try:
            # Temporarily set the tokens for testing
            os.environ["INTERCOM_ACCESS_TOKEN"] = request.intercom_token
            os.environ["OPENAI_API_KEY"] = request.openai_key

            # Test connectivity
            connectivity = await validator.test_connectivity()

            # Determine overall status
            if (
                connectivity.intercom_api == "reachable"
                and connectivity.openai_api == "reachable"
            ):
                status = "valid"
            else:
                status = "invalid"
                if connectivity.intercom_api != "reachable":
                    errors.append(
                        f"Intercom API test failed: {connectivity.intercom_api}"
                    )
                if connectivity.openai_api != "reachable":
                    errors.append(f"OpenAI API test failed: {connectivity.openai_api}")

            session_logger.info(
                f"API key validation completed: {status}",
                event="validation_complete",
                data={
                    "status": status,
                    "intercom_status": connectivity.intercom_api,
                    "openai_status": connectivity.openai_api,
                    "errors": errors,
                },
            )

            return ValidationResponse(
                status=status,
                environment=environment,
                connectivity=connectivity.dict(),
                errors=errors,
            )

        finally:
            # Restore original environment
            if old_intercom:
                os.environ["INTERCOM_ACCESS_TOKEN"] = old_intercom
            else:
                os.environ.pop("INTERCOM_ACCESS_TOKEN", None)

            if old_openai:
                os.environ["OPENAI_API_KEY"] = old_openai
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    except Exception as e:
        session_logger.error(
            f"API key validation failed: {str(e)}",
            event="validation_error",
            exc_info=True,
        )

        return ValidationResponse(
            status="error",
            environment={"intercom_token": "error", "openai_key": "error"},
            connectivity={"intercom_api": "error", "openai_api": "error"},
            errors=[f"Validation failed: {str(e)}"],
        )


@app.get("/api/status", response_model=dict)
async def status():
    """Status endpoint with environment info."""
    return {
        "service": "ask-intercom-api",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "frontend_built": frontend_dir.exists(),
    }


async def generate_sse_events(
    query: str, config: Config, session_id: str, request_id: str
) -> AsyncGenerator[str, None]:
    """Generate SSE events during query processing."""

    def send_event(event_type: str, data: dict) -> str:
        """Format data as SSE event."""
        json_data = json.dumps(data)
        return f"event: {event_type}\ndata: {json_data}\n\n"

    try:
        # Progress: Starting
        yield send_event(
            "progress",
            {
                "stage": "starting",
                "message": "Initializing query processor...",
                "percent": 0,
            },
        )

        processor = QueryProcessor(config)

        # Progress: Fetching app ID
        yield send_event(
            "progress",
            {
                "stage": "initializing",
                "message": "Fetching Intercom app configuration...",
                "percent": 5,
            },
        )

        # We need to capture logs to send as progress events
        # For now, we'll add strategic yield points

        # Progress: Interpreting timeframe
        yield send_event(
            "progress",
            {
                "stage": "timeframe",
                "message": "Interpreting query timeframe...",
                "percent": 10,
            },
        )

        # Start processing
        start_time = time()

        # Create a shared progress state that can be updated from callbacks
        progress_state = {
            "stage": "starting",
            "message": "Initializing query processor...",
            "percent": 0,
            "conversation_count": 0,
            "ai_started": False,
            "ai_start_time": None,
        }

        # Real progress callback that updates shared state
        async def progress_callback(stage: str, message: str, percent: int):
            progress_state.update(
                {"stage": stage, "message": message, "percent": percent}
            )
            # Special handling for conversation count
            if "conversations to analyze" in message:
                import re

                match = re.search(r"(\d+) conversations", message)
                if match:
                    progress_state["conversation_count"] = int(match.group(1))

            # Track when AI analysis starts
            if stage == "analyzing" and not progress_state["ai_started"]:
                progress_state["ai_started"] = True
                progress_state["ai_start_time"] = time()

        # Initial progress
        yield send_event(
            "progress",
            {
                "stage": progress_state["stage"],
                "message": progress_state["message"],
                "percent": progress_state["percent"],
            },
        )

        # Start processing in background with real progress callback
        processor_task = asyncio.create_task(
            processor.process_query(query, progress_callback=progress_callback)
        )

        # Dynamic progress updates while processing
        last_percent = 0

        while not processor_task.done():
            await asyncio.sleep(0.8)  # Check every 800ms

            current = progress_state.copy()

            # Add AI analysis progress estimation
            if current["ai_started"] and current["ai_start_time"]:
                ai_elapsed = time() - current["ai_start_time"]
                # Estimate 0.3-0.5 seconds per conversation for AI analysis
                estimated_ai_time = max(current["conversation_count"] * 0.4, 10)
                ai_progress = min(ai_elapsed / estimated_ai_time, 0.95)

                if current["stage"] == "analyzing":
                    # Smooth AI progress from 75% to 90%
                    ai_percent = 75 + (ai_progress * 15)
                    current["percent"] = min(int(ai_percent), 90)

                    # Update message based on progress
                    if ai_progress < 0.3:
                        current[
                            "message"
                        ] = f"Analyzing with {processor.config.model}..."
                    elif ai_progress < 0.7:
                        current[
                            "message"
                        ] = f"Generating structured insights with {processor.config.model}..."
                    else:
                        current["message"] = "Categorizing and prioritizing insights..."

            # Only send update if progress changed
            if current["percent"] != last_percent or current[
                "message"
            ] != progress_state.get("last_message", ""):
                yield send_event(
                    "progress",
                    {
                        "stage": current["stage"],
                        "message": current["message"],
                        "percent": current["percent"],
                    },
                )
                last_percent = current["percent"]
                progress_state["last_message"] = current["message"]

        # Get the completed result
        result = await processor_task

        # Final progress update
        yield send_event(
            "progress",
            {
                "stage": "finalizing",
                "message": "Analysis complete!",
                "percent": 100,
            },
        )

        # Progress: Complete
        duration_ms = int((time() - start_time) * 1000)

        # Log completion
        session_logger.log_query_complete(
            query,
            {
                "conversation_count": result.conversation_count,
                "insights": result.key_insights,
                "cost": result.cost_info.estimated_cost_usd,
                "tokens_used": result.cost_info.tokens_used,
            },
            duration_ms,
        )

        # Update session
        session_manager.log_session_query(
            session_id,
            query,
            {
                "insights": result.key_insights,
                "cost": result.cost_info.estimated_cost_usd,
                "conversation_count": result.conversation_count,
            },
            duration_ms,
        )

        # Get structured result if available
        structured_result = processor.get_last_structured_result()

        if structured_result:
            # Send structured result
            structured_insights = []
            for insight in structured_result.insights:
                structured_insights.append(
                    {
                        "id": insight.id,
                        "category": insight.category,
                        "title": insight.title,
                        "description": insight.description,
                        "impact": {
                            "customer_count": insight.impact.customer_count,
                            "percentage": insight.impact.percentage,
                            "severity": insight.impact.severity,
                        },
                        "customers": [
                            {
                                "email": customer.email,
                                "conversation_id": customer.conversation_id,
                                "intercom_url": customer.intercom_url,
                                "issue_summary": customer.issue_summary,
                            }
                            for customer in insight.customers
                        ],
                        "priority_score": insight.priority_score,
                        "recommendation": insight.recommendation,
                    }
                )

            yield send_event(
                "complete",
                {
                    "insights": structured_insights,
                    "summary": {
                        "total_conversations": structured_result.summary.total_conversations,
                        "total_messages": structured_result.summary.total_messages,
                        "analysis_timestamp": structured_result.summary.analysis_timestamp.isoformat(),
                    },
                    "cost": result.cost_info.estimated_cost_usd,
                    "response_time_ms": duration_ms,
                    "session_id": session_id,
                    "request_id": request_id,
                },
            )
        else:
            # Fallback to legacy format
            yield send_event(
                "complete",
                {
                    "insights": result.key_insights,
                    "summary": result.summary,
                    "cost": result.cost_info.estimated_cost_usd,
                    "response_time_ms": duration_ms,
                    "conversation_count": result.conversation_count,
                    "session_id": session_id,
                    "request_id": request_id,
                },
            )

    except Exception as e:
        session_logger.error(
            f"SSE processing error: {str(e)}",
            event="sse_error",
            data={"query": query},
            exc_info=True,
        )

        yield send_event(
            "error",
            {
                "error_category": "processing_error",
                "message": str(e),
                "user_action": "Please try again or contact support",
                "retryable": True,
                "session_id": session_id,
                "request_id": request_id,
            },
        )


@app.post("/api/analyze/stream")
async def analyze_conversations_stream(request: AnalysisRequest, http_request: Request):
    """Stream analysis progress using Server-Sent Events."""
    session_id = http_request.headers.get("X-Session-ID", "unknown")
    request_id = http_request.headers.get("X-Request-ID", "unknown")

    # Log query start
    session_logger.log_query_start(
        request.query, {"max_conversations": request.max_conversations}
    )

    # Get tokens from request or environment
    intercom_token = request.intercom_token or os.getenv("INTERCOM_ACCESS_TOKEN")
    openai_key = request.openai_key or os.getenv("OPENAI_API_KEY")

    # Validate tokens (same as regular endpoint)
    if not intercom_token:
        raise APIError(
            category="environment_error",
            message="Intercom access token is missing",
            user_action="Please provide your Intercom access token in the API Key Setup section",
            retryable=True,
            status_code=400,
        )

    if not openai_key:
        raise APIError(
            category="environment_error",
            message="OpenAI API key is missing",
            user_action="Please provide your OpenAI API key in the API Key Setup section",
            retryable=True,
            status_code=400,
        )

    # Calculate smart max_conversations
    smart_max, adjustment_msg = get_smart_max_conversations(
        request.query, request.max_conversations
    )

    # Log adjustment if made
    if adjustment_msg:
        session_logger.info(
            f"Smart limit adjustment: {adjustment_msg}",
            event="smart_limit_adjustment",
            session_id=session_id,
            request_id=request_id,
            data={
                "query": request.query,
                "adjusted_max": smart_max,
                "message": adjustment_msg,
            },
        )

    # Create config
    config = Config(
        intercom_token=intercom_token,
        openai_key=openai_key,
        max_conversations=smart_max,
    )

    # Return SSE response
    return StreamingResponse(
        generate_sse_events(request.query, config, session_id, request_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_conversations(request: AnalysisRequest, http_request: Request):
    """
    Analyze Intercom conversations and return insights.

    This endpoint wraps the existing CLI functionality with enhanced error handling.
    """
    session_id = http_request.headers.get("X-Session-ID", "unknown")
    request_id = http_request.headers.get("X-Request-ID", "unknown")

    try:
        # Log query start
        session_logger.log_query_start(
            request.query, {"max_conversations": request.max_conversations}
        )

        # Get tokens from request or environment
        intercom_token = request.intercom_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        openai_key = request.openai_key or os.getenv("OPENAI_API_KEY")

        # Enhanced validation with specific error messages
        if not intercom_token:
            raise APIError(
                category="environment_error",
                message="Intercom access token is missing",
                user_action="Please provide your Intercom access token in the API Key Setup section",
                retryable=True,
                status_code=400,
            )

        if not openai_key:
            raise APIError(
                category="environment_error",
                message="OpenAI API key is missing",
                user_action="Please provide your OpenAI API key in the API Key Setup section",
                retryable=True,
                status_code=400,
            )

        # Validate key formats
        if not openai_key.startswith("sk-"):
            raise APIError(
                category="validation_error",
                message="OpenAI API key has invalid format",
                user_action="OpenAI keys should start with 'sk-'. Please check your key.",
                retryable=True,
                status_code=400,
            )

        # Calculate smart max_conversations
        smart_max, adjustment_msg = get_smart_max_conversations(
            request.query, request.max_conversations
        )

        # Log adjustment if made
        if adjustment_msg:
            session_logger.info(
                f"Smart limit adjustment: {adjustment_msg}",
                event="smart_limit_adjustment",
                session_id=session_id,
                request_id=request_id,
                data={
                    "query": request.query,
                    "adjusted_max": smart_max,
                    "message": adjustment_msg,
                },
            )

        # Create config with validated keys
        try:
            config = Config(
                intercom_token=intercom_token,
                openai_key=openai_key,
                max_conversations=smart_max,
            )
        except Exception as e:
            raise APIError(
                category="environment_error",
                message=f"Configuration error: {str(e)}",
                user_action="Please check your API keys and try again",
                retryable=True,
                status_code=400,
            ) from e

        # Process the query using existing CLI logic
        start_time = time()
        try:
            processor = QueryProcessor(config)
            result = await processor.process_query(request.query)
        except Exception as e:
            # Log the processing error
            session_logger.log_api_error(
                "query_processor",
                "processing_error",
                str(e),
                {
                    "query": request.query,
                    "config": {"max_conversations": request.max_conversations},
                },
            )

            # Determine error type and provide helpful message
            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                raise APIError(
                    category="connectivity_error",
                    message="API authentication failed",
                    user_action="Please check that your API keys are valid and have the correct permissions",
                    retryable=True,
                    status_code=401,
                ) from e
            elif "rate limit" in error_str or "429" in error_str:
                raise APIError(
                    category="rate_limit_error",
                    message="API rate limit exceeded",
                    user_action="Please wait a few minutes and try again",
                    retryable=True,
                    status_code=429,
                ) from e
            elif "connection" in error_str or "timeout" in error_str:
                raise APIError(
                    category="connectivity_error",
                    message="Unable to connect to external services",
                    user_action="Please check your internet connection and try again",
                    retryable=True,
                    status_code=503,
                ) from e
            else:
                raise APIError(
                    category="processing_error",
                    message=f"Query processing failed: {str(e)}",
                    user_action="Please try again with a different query or contact support",
                    retryable=False,
                    status_code=500,
                ) from e

        end_time = time()
        duration_ms = int((end_time - start_time) * 1000)

        # Log successful completion
        session_logger.log_query_complete(
            request.query,
            {
                "conversation_count": result.conversation_count,
                "insights": result.key_insights,
                "cost": result.cost_info.estimated_cost_usd,
                "tokens_used": result.cost_info.tokens_used,
            },
            duration_ms,
        )

        # Update session with query data
        session_manager.log_session_query(
            session_id,
            request.query,
            {
                "insights": result.key_insights,
                "cost": result.cost_info.estimated_cost_usd,
                "conversation_count": result.conversation_count,
            },
            duration_ms,
        )

        # Transform CLI result to API response
        return AnalysisResponse(
            insights=result.key_insights,
            summary=result.summary,  # Include full analysis with URLs
            cost=result.cost_info.estimated_cost_usd,
            response_time_ms=duration_ms,
            conversation_count=result.conversation_count,
            session_id=session_id,
            request_id=request_id,
        )

    except APIError as e:
        # Log API errors with context
        session_logger.error(
            f"API error: {e.category} - {e.detail}",
            event="api_error",
            data={
                "category": e.category,
                "message": e.detail,
                "user_action": e.user_action,
                "retryable": e.retryable,
                "query": request.query,
            },
        )

        # Return structured error response
        error_response = ErrorResponse(
            error_category=e.category,
            message=e.detail,
            user_action=e.user_action,
            retryable=e.retryable,
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        raise HTTPException(
            status_code=e.status_code, detail=error_response.dict()
        ) from None

    except Exception as e:
        # Log unexpected errors
        session_logger.error(
            f"Unexpected error in analyze endpoint: {str(e)}",
            event="unexpected_error",
            data={"query": request.query},
            exc_info=True,
        )

        # Return generic error response
        error_response = ErrorResponse(
            error_category="processing_error",
            message="An unexpected error occurred",
            user_action="Please try again or contact support if the problem persists",
            retryable=True,
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        raise HTTPException(status_code=500, detail=error_response.dict()) from e


@app.post("/api/analyze/structured", response_model=StructuredAnalysisResponse)
async def analyze_conversations_structured(
    request: AnalysisRequest, http_request: Request
):
    """
    Analyze Intercom conversations and return structured insights.

    This endpoint returns the new structured JSON format instead of legacy text parsing.
    """
    session_id = http_request.headers.get("X-Session-ID", "unknown")
    request_id = http_request.headers.get("X-Request-ID", "unknown")

    try:
        # Log query start
        session_logger.log_query_start(
            request.query, {"max_conversations": request.max_conversations}
        )

        # Get tokens from request or environment
        intercom_token = request.intercom_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        openai_key = request.openai_key or os.getenv("OPENAI_API_KEY")

        # Validate tokens (same validation as regular endpoint)
        if not intercom_token:
            raise APIError(
                category="environment_error",
                message="Intercom access token is missing",
                user_action="Please provide your Intercom access token in the API Key Setup section",
                retryable=True,
                status_code=400,
            )

        if not openai_key:
            raise APIError(
                category="environment_error",
                message="OpenAI API key is missing",
                user_action="Please provide your OpenAI API key in the API Key Setup section",
                retryable=True,
                status_code=400,
            )

        if not openai_key.startswith("sk-"):
            raise APIError(
                category="validation_error",
                message="OpenAI API key has invalid format",
                user_action="OpenAI keys should start with 'sk-'. Please check your key.",
                retryable=True,
                status_code=400,
            )

        # Calculate smart max_conversations
        smart_max, adjustment_msg = get_smart_max_conversations(
            request.query, request.max_conversations
        )

        # Log adjustment if made
        if adjustment_msg:
            session_logger.info(
                f"Smart limit adjustment: {adjustment_msg}",
                event="smart_limit_adjustment",
                session_id=session_id,
                request_id=request_id,
                data={
                    "query": request.query,
                    "adjusted_max": smart_max,
                    "message": adjustment_msg,
                },
            )

        # Create config
        try:
            config = Config(
                intercom_token=intercom_token,
                openai_key=openai_key,
                max_conversations=smart_max,
            )
        except Exception as e:
            raise APIError(
                category="environment_error",
                message=f"Configuration error: {str(e)}",
                user_action="Please check your API keys and try again",
                retryable=True,
                status_code=400,
            ) from e

        # Process the query
        start_time = time()
        try:
            processor = QueryProcessor(config)
            legacy_result = await processor.process_query(request.query)
            structured_result = processor.get_last_structured_result()

            if not structured_result:
                raise APIError(
                    category="processing_error",
                    message="Structured analysis not available",
                    user_action="The analysis fell back to legacy mode. Try again or use the regular analyze endpoint.",
                    retryable=True,
                    status_code=500,
                )

        except APIError:
            raise  # Re-raise API errors
        except Exception as e:
            # Handle processing errors the same way as regular endpoint
            session_logger.log_api_error(
                "query_processor",
                "processing_error",
                str(e),
                {
                    "query": request.query,
                    "config": {"max_conversations": request.max_conversations},
                },
            )

            error_str = str(e).lower()
            if "unauthorized" in error_str or "401" in error_str:
                raise APIError(
                    category="connectivity_error",
                    message="API authentication failed",
                    user_action="Please check that your API keys are valid and have the correct permissions",
                    retryable=True,
                    status_code=401,
                ) from e
            elif "rate limit" in error_str or "429" in error_str:
                raise APIError(
                    category="rate_limit_error",
                    message="API rate limit exceeded",
                    user_action="Please wait a few minutes and try again",
                    retryable=True,
                    status_code=429,
                ) from e
            elif "connection" in error_str or "timeout" in error_str:
                raise APIError(
                    category="connectivity_error",
                    message="Unable to connect to external services",
                    user_action="Please check your internet connection and try again",
                    retryable=True,
                    status_code=503,
                ) from e
            else:
                raise APIError(
                    category="processing_error",
                    message=f"Query processing failed: {str(e)}",
                    user_action="Please try again with a different query or contact support",
                    retryable=False,
                    status_code=500,
                ) from e

        end_time = time()
        duration_ms = int((end_time - start_time) * 1000)

        # Log successful completion
        session_logger.log_query_complete(
            request.query,
            {
                "conversation_count": structured_result.summary.total_conversations,
                "insights": [insight.title for insight in structured_result.insights],
                "cost": legacy_result.cost_info.estimated_cost_usd,
                "tokens_used": legacy_result.cost_info.tokens_used,
            },
            duration_ms,
        )

        # Update session
        session_manager.log_session_query(
            session_id,
            request.query,
            {
                "insights": [insight.title for insight in structured_result.insights],
                "cost": legacy_result.cost_info.estimated_cost_usd,
                "conversation_count": structured_result.summary.total_conversations,
            },
            duration_ms,
        )

        # Convert structured result to API response
        structured_insights = []
        for insight in structured_result.insights:
            structured_insights.append(
                StructuredInsight(
                    id=insight.id,
                    category=insight.category,
                    title=insight.title,
                    description=insight.description,
                    impact=StructuredInsightImpact(
                        customer_count=insight.impact.customer_count,
                        percentage=insight.impact.percentage,
                        severity=insight.impact.severity,
                    ),
                    customers=[
                        StructuredInsightCustomer(
                            email=customer.email,
                            conversation_id=customer.conversation_id,
                            intercom_url=customer.intercom_url,
                            issue_summary=customer.issue_summary,
                        )
                        for customer in insight.customers
                    ],
                    priority_score=insight.priority_score,
                    recommendation=insight.recommendation,
                )
            )

        return StructuredAnalysisResponse(
            insights=structured_insights,
            summary=StructuredAnalysisSummary(
                total_conversations=structured_result.summary.total_conversations,
                total_messages=structured_result.summary.total_messages,
                analysis_timestamp=structured_result.summary.analysis_timestamp.isoformat(),
            ),
            cost=legacy_result.cost_info.estimated_cost_usd,
            response_time_ms=duration_ms,
            session_id=session_id,
            request_id=request_id,
        )

    except APIError as e:
        # Same error handling as regular endpoint
        session_logger.error(
            f"API error: {e.category} - {e.detail}",
            event="api_error",
            data={
                "category": e.category,
                "message": e.detail,
                "user_action": e.user_action,
                "retryable": e.retryable,
                "query": request.query,
            },
        )

        error_response = ErrorResponse(
            error_category=e.category,
            message=e.detail,
            user_action=e.user_action,
            retryable=e.retryable,
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        raise HTTPException(
            status_code=e.status_code, detail=error_response.dict()
        ) from None

    except Exception as e:
        # Same unexpected error handling
        session_logger.error(
            f"Unexpected error in structured analyze endpoint: {str(e)}",
            event="unexpected_error",
            data={"query": request.query},
            exc_info=True,
        )

        error_response = ErrorResponse(
            error_category="processing_error",
            message="An unexpected error occurred",
            user_action="Please try again or contact support if the problem persists",
            retryable=True,
            session_id=session_id,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        raise HTTPException(status_code=500, detail=error_response.dict()) from e


# Serve frontend static files (for production) - MUST be last to avoid catching API routes
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
