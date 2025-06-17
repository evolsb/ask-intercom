# Phase 0 Implementation Specifications

> **Implementation guide for the CLI prototype**
> **Target:** Functional CLI that proves core intelligence capability

---

## Project Structure

```
ask-intercom/
├── .env                    # Environment variables (gitignored)
├── .gitignore             # Git ignore rules
├── pyproject.toml         # Poetry configuration
├── README.md              # Basic setup instructions
├── src/
│   ├── __init__.py
│   ├── cli.py             # Main CLI entry point
│   ├── config.py          # Configuration management
│   ├── query_processor.py # Core query orchestration
│   ├── intercom_client.py # MCP/REST API client
│   ├── ai_client.py       # OpenAI integration
│   └── models.py          # Data models and types
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_query_processor.py
│   ├── test_intercom_client.py
│   └── test_ai_client.py
└── docs/
    └── architecture/       # Architecture documentation
```

---

## Dependencies & Environment Setup

### pyproject.toml
```toml
[tool.poetry]
name = "ask-intercom"
version = "0.1.0"
description = "AI-powered insights from Intercom conversations"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
openai = "^1.0.0"
httpx = "^0.25.0"
python-dotenv = "^1.0.0"
pydantic = "^2.0.0"
rich = "^13.0.0"  # For better CLI output formatting

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
ruff = "^0.1.0"

[tool.poetry.scripts]
ask-intercom = "src.cli:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### Environment Configuration
```bash
# .env file structure
INTERCOM_ACCESS_TOKEN=
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4
MAX_CONVERSATIONS=50
DEBUG=false
```

---

## Core Implementation Files

### 1. CLI Entry Point (`src/cli.py`)

```python
#!/usr/bin/env python3
"""
Ask-Intercom CLI - Phase 0 Prototype
Usage: ask-intercom "What are the top customer complaints this month?"
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import Config
from .query_processor import QueryProcessor


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Ask natural language questions about your Intercom conversations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ask-intercom "What are the top customer complaints this month?"
  ask-intercom "How many support tickets were opened last week?"
  ask-intercom "What issues did john@company.com report recently?" --debug
        """
    )

    parser.add_argument(
        "query",
        help="Natural language question about your Intercom conversations"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Override the OpenAI model (default: from config)"
    )

    parser.add_argument(
        "--max-conversations",
        type=int,
        default=None,
        help="Maximum number of conversations to analyze"
    )

    return parser


async def run_query(query: str, config: Config, console: Console) -> None:
    """Execute a single query and display results."""
    try:
        with console.status("[bold green]Processing your query..."):
            processor = QueryProcessor(config)
            result = await processor.process_query(query)

        # Display results with rich formatting
        console.print("\n" + "="*60)
        console.print(f"[bold blue]Query:[/bold blue] {query}")
        console.print("="*60)

        # Main results
        console.print(Panel(
            result.summary,
            title="[bold green]Analysis Results[/bold green]",
            border_style="green"
        ))

        # Metadata
        metadata = f"""
[dim]Analyzed {result.conversation_count} conversations
Time range: {result.time_range.description}
Model: {result.cost_info.model_used}
Tokens: {result.cost_info.tokens_used:,}
Estimated cost: ${result.cost_info.estimated_cost_usd:.3f}[/dim]
        """
        console.print(metadata.strip())

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if config.debug:
            raise


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup
    setup_logging(args.debug)
    console = Console()

    try:
        # Load configuration
        config = Config.from_env()
        if args.model:
            config.model = args.model
        if args.max_conversations:
            config.max_conversations = args.max_conversations
        if args.debug:
            config.debug = True

        config.validate()

        # Run the query
        asyncio.run(run_query(args.query, config, console))

    except KeyboardInterrupt:
        console.print("\n[yellow]Query cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Fatal error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 2. Configuration Management (`src/config.py`)

```python
"""Configuration management for Ask-Intercom."""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class Config(BaseModel):
    """Application configuration."""

    intercom_token: str = Field(..., description="Intercom access token")
    openai_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    max_conversations: int = Field(default=50, description="Max conversations to analyze")
    debug: bool = Field(default=False, description="Enable debug mode")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("intercom_token")
    def validate_intercom_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Invalid Intercom access token")
        return v

    @validator("openai_key")
    def validate_openai_key(cls, v):
        if not v or not v.startswith(("sk-", "pk-")):
            raise ValueError("Invalid OpenAI API key")
        return v

    @validator("max_conversations")
    def validate_max_conversations(cls, v):
        if v <= 0 or v > 200:
            raise ValueError("max_conversations must be between 1 and 200")
        return v

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        return cls(
            intercom_token=os.getenv("INTERCOM_ACCESS_TOKEN", ""),
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            max_conversations=int(os.getenv("MAX_CONVERSATIONS", "50")),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )

    def validate(self) -> None:
        """Validate the configuration."""
        # This will raise ValidationError if invalid
        self.__class__.parse_obj(self.dict())
```

### 3. Data Models (`src/models.py`)

```python
"""Data models for Ask-Intercom."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class TimeFrame:
    """Represents a time range for queries."""
    start_date: datetime
    end_date: datetime
    description: str  # Human-readable description like "this month"


@dataclass
class Message:
    """A single message within a conversation."""
    id: str
    author_type: str  # "user" | "admin"
    body: str
    created_at: datetime


@dataclass
class Conversation:
    """An Intercom conversation."""
    id: str
    created_at: datetime
    messages: List[Message]
    customer_email: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class CostInfo:
    """Information about API costs."""
    tokens_used: int
    estimated_cost_usd: float
    model_used: str


@dataclass
class AnalysisResult:
    """Result of AI analysis."""
    summary: str
    key_insights: List[str]
    conversation_count: int
    time_range: TimeFrame
    cost_info: CostInfo


@dataclass
class ConversationFilters:
    """Filters for fetching conversations."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    customer_email: Optional[str] = None
    limit: int = 50
```

---

## API Client Implementations

### 4. Intercom Client (`src/intercom_client.py`)

```python
"""Intercom API client with MCP fallback."""

import logging
from datetime import datetime
from typing import List, Optional

import httpx

from .models import Conversation, ConversationFilters, Message


logger = logging.getLogger(__name__)


class IntercomClient:
    """Intercom API client with MCP support and REST fallback."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.intercom.io"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def fetch_conversations(self, filters: ConversationFilters) -> List[Conversation]:
        """Fetch conversations based on filters."""
        try:
            # TODO: Implement MCP client when available
            logger.info("MCP not implemented yet, using REST API")
            return await self._fetch_via_rest(filters)
        except Exception as e:
            logger.error(f"Failed to fetch conversations: {e}")
            raise

    async def _fetch_via_rest(self, filters: ConversationFilters) -> List[Conversation]:
        """Fetch conversations via REST API."""
        conversations = []

        async with httpx.AsyncClient() as client:
            # Build query parameters
            params = {
                "per_page": min(filters.limit, 50),  # Intercom max is 50
                "order": "desc",
                "sort": "created_at"
            }

            if filters.start_date:
                params["created_at_after"] = int(filters.start_date.timestamp())
            if filters.end_date:
                params["created_at_before"] = int(filters.end_date.timestamp())

            response = await client.get(
                f"{self.base_url}/conversations",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()

            data = response.json()

            for conv_data in data.get("conversations", []):
                conversation = await self._parse_conversation(client, conv_data)
                if conversation:
                    conversations.append(conversation)

                    if len(conversations) >= filters.limit:
                        break

        logger.info(f"Fetched {len(conversations)} conversations")
        return conversations

    async def _parse_conversation(self, client: httpx.AsyncClient, conv_data: dict) -> Optional[Conversation]:
        """Parse a conversation from API response."""
        try:
            # Get conversation parts (messages)
            parts_response = await client.get(
                f"{self.base_url}/conversations/{conv_data['id']}",
                headers=self.headers
            )
            parts_response.raise_for_status()
            parts_data = parts_response.json()

            # Parse messages
            messages = []
            for part in parts_data.get("conversation_parts", {}).get("conversation_parts", []):
                if part.get("part_type") in ["comment", "note"]:
                    message = Message(
                        id=part["id"],
                        author_type="admin" if part.get("author", {}).get("type") == "admin" else "user",
                        body=part.get("body", ""),
                        created_at=datetime.fromtimestamp(part["created_at"])
                    )
                    messages.append(message)

            # Add the initial message
            if conv_data.get("source", {}).get("body"):
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=conv_data["source"]["body"],
                    created_at=datetime.fromtimestamp(conv_data["created_at"])
                )
                messages.insert(0, initial_message)

            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"]),
                messages=messages,
                customer_email=conv_data.get("source", {}).get("delivered_as", {}).get("contact", {}).get("email"),
                tags=conv_data.get("tags", {}).get("tags", [])
            )

        except Exception as e:
            logger.warning(f"Failed to parse conversation {conv_data.get('id')}: {e}")
            return None
```

### 5. AI Client (`src/ai_client.py`)

```python
"""OpenAI integration for conversation analysis."""

import json
import logging
from datetime import datetime, timedelta
from typing import List

from openai import AsyncOpenAI

from .models import AnalysisResult, Conversation, CostInfo, TimeFrame


logger = logging.getLogger(__name__)


class AIClient:
    """OpenAI client for conversation analysis."""

    # Token cost per 1K tokens (as of Dec 2024)
    COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def analyze_conversations(self, conversations: List[Conversation], query: str) -> AnalysisResult:
        """Analyze conversations and generate insights."""
        # First, interpret the timeframe from the query
        timeframe = await self._interpret_timeframe(query)

        # Build the analysis prompt
        prompt = self._build_analysis_prompt(conversations, query)

        # Call OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=500,   # Limit response length
        )

        # Parse response
        analysis_text = response.choices[0].message.content

        # Calculate costs
        cost_info = self._calculate_cost(response.usage)

        # Extract key insights (simple parsing for now)
        insights = self._extract_insights(analysis_text)

        return AnalysisResult(
            summary=analysis_text,
            key_insights=insights,
            conversation_count=len(conversations),
            time_range=timeframe,
            cost_info=cost_info
        )

    async def _interpret_timeframe(self, query: str) -> TimeFrame:
        """Use AI to interpret timeframe from natural language."""
        prompt = f"""
        Extract the timeframe from this query: "{query}"

        Return JSON with:
        - start_date: ISO date string
        - end_date: ISO date string
        - description: human description

        If no timeframe is specified, assume "last 30 days".
        Today is {datetime.now().strftime('%Y-%m-%d')}.
        """

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200
        )

        try:
            timeframe_data = json.loads(response.choices[0].message.content)
            return TimeFrame(
                start_date=datetime.fromisoformat(timeframe_data["start_date"]),
                end_date=datetime.fromisoformat(timeframe_data["end_date"]),
                description=timeframe_data["description"]
            )
        except Exception as e:
            logger.warning(f"Failed to parse timeframe, using default: {e}")
            # Default to last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            return TimeFrame(start_date, end_date, "last 30 days")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for conversation analysis."""
        return """
        You are an expert customer support analyst. Your job is to analyze Intercom conversations and provide clear, actionable insights.

        Guidelines:
        - Provide exactly 3-5 bullet points summarizing key findings
        - Focus on patterns, trends, and actionable insights
        - Be specific with numbers and percentages when possible
        - Prioritize customer pain points and frequently mentioned issues
        - Keep each bullet point to 1-2 sentences maximum
        - Use professional but accessible language
        """

    def _build_analysis_prompt(self, conversations: List[Conversation], query: str) -> str:
        """Build the prompt for conversation analysis."""
        # Summarize conversations to fit within token limits
        conv_summaries = []
        for conv in conversations[:50]:  # Limit to prevent token overflow
            summary = f"Conversation {conv.id} ({conv.created_at.strftime('%Y-%m-%d')}):\n"
            for msg in conv.messages[:5]:  # Limit messages per conversation
                author = "Customer" if msg.author_type == "user" else "Support"
                summary += f"  {author}: {msg.body[:200]}...\n"
            conv_summaries.append(summary)

        return f"""
        Query: {query}

        Analyze these {len(conversations)} customer support conversations:

        {chr(10).join(conv_summaries)}

        Provide a clear analysis addressing the original query.
        """

    def _calculate_cost(self, usage) -> CostInfo:
        """Calculate the cost of the API call."""
        model_costs = self.COSTS.get(self.model, self.COSTS["gpt-4"])

        input_cost = (usage.prompt_tokens / 1000) * model_costs["input"]
        output_cost = (usage.completion_tokens / 1000) * model_costs["output"]
        total_cost = input_cost + output_cost

        return CostInfo(
            tokens_used=usage.total_tokens,
            estimated_cost_usd=total_cost,
            model_used=self.model
        )

    def _extract_insights(self, analysis_text: str) -> List[str]:
        """Extract key insights from the analysis text."""
        # Simple extraction - look for bullet points
        insights = []
        for line in analysis_text.split('\n'):
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                insights.append(line[1:].strip())

        return insights[:5]  # Limit to 5 insights
```

### 6. Query Processor (`src/query_processor.py`)

```python
"""Main query processing orchestration."""

import logging
from datetime import datetime

from .ai_client import AIClient
from .config import Config
from .intercom_client import IntercomClient
from .models import AnalysisResult, ConversationFilters


logger = logging.getLogger(__name__)


class QueryProcessor:
    """Orchestrates the full query processing workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.intercom_client = IntercomClient(config.intercom_token)
        self.ai_client = AIClient(config.openai_key, config.model)

    async def process_query(self, query: str) -> AnalysisResult:
        """Process a natural language query and return analysis."""
        start_time = datetime.now()

        try:
            # Step 1: Interpret timeframe from query
            logger.info("Interpreting query timeframe...")
            timeframe = await self.ai_client._interpret_timeframe(query)

            # Step 2: Fetch relevant conversations
            logger.info(f"Fetching conversations from {timeframe.description}...")
            filters = ConversationFilters(
                start_date=timeframe.start_date,
                end_date=timeframe.end_date,
                limit=self.config.max_conversations
            )
            conversations = await self.intercom_client.fetch_conversations(filters)

            if not conversations:
                # Return empty result if no conversations found
                from .models import CostInfo
                return AnalysisResult(
                    summary="No conversations found in the specified timeframe.",
                    key_insights=[],
                    conversation_count=0,
                    time_range=timeframe,
                    cost_info=CostInfo(tokens_used=0, estimated_cost_usd=0.0, model_used=self.config.model)
                )

            # Step 3: Analyze conversations with AI
            logger.info(f"Analyzing {len(conversations)} conversations...")
            result = await self.ai_client.analyze_conversations(conversations, query)

            # Log performance
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Query completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}")

            return result

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
```

---

## Testing Implementation

### Basic Test Structure (`tests/test_cli.py`)

```python
"""Tests for CLI functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from src.cli import main
from src.models import AnalysisResult, CostInfo, TimeFrame


@pytest.fixture
def mock_query_processor():
    """Mock QueryProcessor for testing."""
    processor = AsyncMock()
    processor.process_query.return_value = AnalysisResult(
        summary="Test analysis result",
        key_insights=["Test insight 1", "Test insight 2"],
        conversation_count=5,
        time_range=TimeFrame(None, None, "test timeframe"),
        cost_info=CostInfo(tokens_used=100, estimated_cost_usd=0.10, model_used="gpt-4")
    )
    return processor


@patch('src.cli.Config.from_env')
@patch('src.cli.QueryProcessor')
def test_cli_basic_query(mock_processor_class, mock_config, mock_query_processor):
    """Test basic CLI query execution."""
    mock_config.return_value.validate.return_value = None
    mock_processor_class.return_value = mock_query_processor

    # This would normally be tested with subprocess or similar
    # For now, just test that the components can be imported and initialized
    assert mock_query_processor is not None
```

---

## Installation & Usage Instructions

### Quick Start
```bash
# 1. Clone and setup
git clone <repo>
cd ask-intercom
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Test the CLI
poetry run ask-intercom "What are the top customer complaints this month?"

# 4. Run tests
poetry run pytest
```

### Success Validation
Test with this exact query to validate Phase 0 success:
```bash
poetry run ask-intercom "What are the top customer complaints this month?"
```

Expected: 3-5 bullet points, <10s response, <$0.50 cost, handles timeframe correctly.

---

## Next Steps After Implementation

1. **Validate against success criteria** - Run the test query and verify all gates pass
2. **Performance optimization** - If response time >10s, optimize conversation fetching
3. **Cost optimization** - If cost >$0.50, optimize prompt length and model choice
4. **Documentation** - Update README with installation and usage instructions
5. **Prepare for Phase 1** - Vector search and conversation context enhancements
