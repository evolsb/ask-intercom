"""
FastAPI web application wrapping the Ask-Intercom CLI functionality.
"""
import os
from pathlib import Path
from time import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import our existing CLI components
from ..config import Config
from ..query_processor import QueryProcessor

app = FastAPI(
    title="Ask-Intercom API",
    description="Transform Intercom conversations into actionable insights",
    version="0.1.0",
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files (for production)
frontend_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


class HealthResponse(BaseModel):
    status: str
    message: str


class AnalysisRequest(BaseModel):
    query: str
    intercom_token: str | None = None
    openai_key: str | None = None
    max_conversations: int = 50


class AnalysisResponse(BaseModel):
    insights: list[str]
    cost: float
    response_time_ms: int
    conversation_count: int


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", message="Ask-Intercom API is running")


@app.get("/api/status", response_model=dict)
async def status():
    """Status endpoint with environment info."""
    return {
        "service": "ask-intercom-api",
        "version": "0.1.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "frontend_built": frontend_dir.exists(),
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_conversations(request: AnalysisRequest):
    """
    Analyze Intercom conversations and return insights.

    This endpoint wraps the existing CLI functionality.
    """
    try:
        # Get tokens from request or environment
        intercom_token = request.intercom_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        openai_key = request.openai_key or os.getenv("OPENAI_API_KEY")

        # Check if we have required keys before creating Config
        if not intercom_token or not openai_key:
            raise HTTPException(
                status_code=400,
                detail="Missing API keys. Provide in request body or environment variables.",
            )

        # Create config with validated keys
        config = Config(
            intercom_token=intercom_token,
            openai_key=openai_key,
            max_conversations=min(request.max_conversations, 200),  # Hard cap
        )

        # Process the query using existing CLI logic
        start_time = time()
        processor = QueryProcessor(config)
        result = await processor.process_query(request.query)
        end_time = time()

        # Transform CLI result to API response
        return AnalysisResponse(
            insights=result.key_insights,
            cost=result.cost_info.estimated_cost_usd,
            response_time_ms=int((end_time - start_time) * 1000),
            conversation_count=result.conversation_count,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
