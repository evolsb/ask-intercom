"""Data models for Ask-Intercom."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import quote


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

    def get_url(self, app_id: str) -> str:
        """Generate clickable Intercom URL for this conversation."""
        base_url = f"https://app.intercom.com/a/inbox/{app_id}/inbox/search/conversation/{self.id}"
        if self.customer_email:
            # Add customer email as query parameter (URL-encoded)
            encoded_email = quote(self.customer_email)
            return f"{base_url}?query={encoded_email}"
        return base_url


@dataclass
class CostInfo:
    """Information about API costs."""

    tokens_used: int
    estimated_cost_usd: float
    model_used: str

    def __post_init__(self):
        """Validate CostInfo parameters to catch construction errors early."""
        if not isinstance(self.tokens_used, int) or self.tokens_used < 0:
            raise ValueError(
                f"tokens_used must be a non-negative integer, got {self.tokens_used}"
            )

        if (
            not isinstance(self.estimated_cost_usd, (int, float))
            or self.estimated_cost_usd < 0
        ):
            raise ValueError(
                f"estimated_cost_usd must be a non-negative number, got {self.estimated_cost_usd}"
            )

        if not isinstance(self.model_used, str) or not self.model_used.strip():
            raise ValueError(
                f"model_used must be a non-empty string, got {self.model_used}"
            )

    @classmethod
    def from_usage(
        cls, usage_tokens: int, model: str, cost_per_token: float = 0.00003
    ) -> "CostInfo":
        """Create CostInfo from usage data with standard cost calculation.

        Args:
            usage_tokens: Number of tokens used (must be non-negative)
            model: Model name (must be non-empty string)
            cost_per_token: Cost per token in USD (default: GPT-4 estimate)

        Returns:
            CostInfo instance with calculated cost

        Raises:
            ValueError: If parameters are invalid
        """
        if not isinstance(usage_tokens, int) or usage_tokens < 0:
            raise ValueError(
                f"usage_tokens must be non-negative integer, got {usage_tokens}"
            )
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"model must be non-empty string, got {model}")
        if not isinstance(cost_per_token, (int, float)) or cost_per_token < 0:
            raise ValueError(
                f"cost_per_token must be non-negative number, got {cost_per_token}"
            )

        return cls(
            tokens_used=usage_tokens,
            estimated_cost_usd=usage_tokens * cost_per_token,
            model_used=model,
        )

    @classmethod
    def zero_cost(cls, model: str = "unknown") -> "CostInfo":
        """Create a zero-cost CostInfo for fallback scenarios."""
        return cls(tokens_used=0, estimated_cost_usd=0.0, model_used=model)


@dataclass
class AnalysisResult:
    """Result of AI analysis."""

    summary: str
    key_insights: List[str]
    conversation_count: int
    time_range: TimeFrame
    cost_info: CostInfo

    # Timing information for performance analysis
    processing_time_ms: Optional[float] = None
    fetch_time_ms: Optional[float] = None
    analysis_time_ms: Optional[float] = None


@dataclass
class ConversationFilters:
    """Filters for fetching conversations."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    customer_email: Optional[str] = None
    limit: Optional[int] = None


@dataclass
class SessionState:
    """State for interactive sessions with conversation memory."""

    last_query: Optional[str] = None
    last_conversations: Optional[List[Conversation]] = None
    last_analysis: Optional[AnalysisResult] = None
    last_timeframe: Optional[TimeFrame] = None


# Structured AI Output Models


@dataclass
class CustomerInsight:
    """Individual customer insight within a category."""

    email: str
    conversation_id: str
    intercom_url: str
    issue_summary: str


@dataclass
class InsightImpact:
    """Impact metrics for an insight."""

    customer_count: int
    percentage: float
    severity: Literal["low", "medium", "high", "critical"]


@dataclass
class Insight:
    """A structured insight from AI analysis."""

    id: str
    category: Literal[
        "BUG", "FEATURE_REQUEST", "COMPLAINT", "PRAISE", "QUESTION", "OTHER"
    ]
    title: str
    description: str
    impact: InsightImpact
    customers: List[CustomerInsight]
    priority_score: int  # 0-100
    recommendation: str


@dataclass
class AnalysisSummary:
    """Summary statistics for the analysis."""

    total_conversations: int
    total_messages: int
    analysis_timestamp: datetime


@dataclass
class StructuredAnalysisResult:
    """Structured result from AI analysis using JSON schema."""

    insights: List[Insight]
    summary: AnalysisSummary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "insights": [
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
                            "email": c.email,
                            "conversation_id": c.conversation_id,
                            "intercom_url": c.intercom_url,
                            "issue_summary": c.issue_summary,
                        }
                        for c in insight.customers
                    ],
                    "priority_score": insight.priority_score,
                    "recommendation": insight.recommendation,
                }
                for insight in self.insights
            ],
            "summary": {
                "total_conversations": self.summary.total_conversations,
                "total_messages": self.summary.total_messages,
                "analysis_timestamp": self.summary.analysis_timestamp.isoformat(),
            },
        }
