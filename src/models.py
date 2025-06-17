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
