"""OpenAI integration for conversation analysis."""

import json
from datetime import datetime, timedelta
from typing import List

from openai import AsyncOpenAI

from .logger import get_logger
from .models import AnalysisResult, Conversation, CostInfo, TimeFrame

logger = get_logger("ai_client")


class AIClient:
    """OpenAI client for conversation analysis."""

    # Token cost per 1K tokens (as of Dec 2024)
    COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self, api_key: str, model: str = "gpt-4", app_id: str = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.app_id = app_id

    async def analyze_conversations(
        self, conversations: List[Conversation], query: str
    ) -> AnalysisResult:
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
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=500,  # Limit response length
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
            cost_info=cost_info,
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
            max_tokens=200,
        )

        try:
            timeframe_data = json.loads(response.choices[0].message.content)
            return TimeFrame(
                start_date=datetime.fromisoformat(timeframe_data["start_date"]),
                end_date=datetime.fromisoformat(timeframe_data["end_date"]),
                description=timeframe_data["description"],
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
        - Structure each insight with: [CATEGORY] Description (X customers affected, Y% of total)
        - Categories: BUG, FEATURE_REQUEST, CONFUSION, COMPLAINT, PROCESS_ISSUE, OTHER
        - Reference specific customer emails as examples with clickable links (e.g., "reported by user@example.com [View](https://app.intercom.com/a/inbox/{app_id}/inbox/shared/all/conversation/{conv_id})")
        - Include metrics: number of customers affected, percentage of conversations, trend direction
        - Mention total messages analyzed at the end
        - Prioritize by impact (most customers affected first)
        - Keep each bullet point to 1-2 sentences maximum
        - When referencing customers, include a clickable "View" link next to their email

        Example format:
        - [BUG] Login verification failing for mobile users (12 customers, 24% of conversations). Examples: user1@email.com [View](conversation_url), user2@email.com [View](conversation_url)
        - [FEATURE_REQUEST] Dark mode requested by enterprise customers (8 customers, 16% of conversations). Trending up from last week.

        End with: "Analyzed X conversations containing Y total messages."
        """

    def _build_analysis_prompt(
        self, conversations: List[Conversation], query: str
    ) -> str:
        """Build the prompt for conversation analysis."""
        # Count total messages
        total_messages = sum(len(conv.messages) for conv in conversations)

        # Summarize conversations to fit within token limits
        conv_summaries = []
        for conv in conversations[:50]:  # Limit to prevent token overflow
            customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"
            summary = f"Conversation from {customer_id} ({conv.created_at.strftime('%Y-%m-%d')}) [ID: {conv.id}]:\n"
            for msg in conv.messages[:5]:  # Limit messages per conversation
                author = "Customer" if msg.author_type == "user" else "Support"
                summary += f"  {author}: {msg.body[:200]}...\n"
            conv_summaries.append(summary)

        # Build conversation mapping for URLs
        conv_mapping = "\n\nConversation URLs for reference:\n"
        for conv in conversations[:50]:
            if self.app_id:
                customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"
                conv_mapping += f"- {customer_id}: {conv.get_url(self.app_id)}\n"

        analysis_prompt = f"""
        Query: {query}

        Analyze these {len(conversations)} customer support conversations (containing {total_messages} total messages):

        {chr(10).join(conv_summaries)}
        """

        if self.app_id:
            analysis_prompt += (
                conv_mapping
                + "\n\nWhen referencing customers in your analysis, include clickable [View] links using the URLs above.\n\n"
            )

        analysis_prompt += "Provide a clear analysis addressing the original query. Remember to mention the total message count at the end."

        return analysis_prompt

    def _calculate_cost(self, usage) -> CostInfo:
        """Calculate the cost of the API call."""
        model_costs = self.COSTS.get(self.model, self.COSTS["gpt-4"])

        input_cost = (usage.prompt_tokens / 1000) * model_costs["input"]
        output_cost = (usage.completion_tokens / 1000) * model_costs["output"]
        total_cost = input_cost + output_cost

        return CostInfo(
            tokens_used=usage.total_tokens,
            estimated_cost_usd=total_cost,
            model_used=self.model,
        )

    def _extract_insights(self, analysis_text: str) -> List[str]:
        """Extract key insights from the analysis text."""
        # Simple extraction - look for bullet points
        insights = []
        for line in analysis_text.split("\n"):
            line = line.strip()
            if line.startswith("•") or line.startswith("-") or line.startswith("*"):
                insights.append(line[1:].strip())

        return insights[:5]  # Limit to 5 insights
