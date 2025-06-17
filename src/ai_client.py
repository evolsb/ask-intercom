"""OpenAI integration for conversation analysis."""

import re
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

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        app_id: str = None,
        timeframe_model: str = "gpt-3.5-turbo",
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.app_id = app_id
        self.timeframe_model = timeframe_model

    async def analyze_conversations(
        self, conversations: List[Conversation], query: str, timeframe: TimeFrame
    ) -> AnalysisResult:
        """Analyze conversations and generate insights."""
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(conversations, query)

        # Determine if this is a follow-up question
        is_followup = "Answer this specific follow-up question:" in prompt
        system_prompt = (
            self._get_followup_system_prompt()
            if is_followup
            else self._get_system_prompt()
        )

        # Call OpenAI for analysis
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
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
        """Deterministically interpret timeframe from natural language."""
        return self._parse_timeframe_deterministic(query)

    def _parse_timeframe_deterministic(self, query: str) -> TimeFrame:
        """Parse timeframes deterministically to ensure consistency."""
        query_lower = query.lower()
        now = datetime.now()

        # Use consistent timezone-naive datetime for deterministic results
        end_time = now.replace(microsecond=0)

        logger.info(f"Parsing timeframe from query: '{query}'")

        # 1. Hour patterns
        if re.search(r"\b(last|past)\s+(1\s+)?hour\b", query_lower):
            start_time = end_time - timedelta(hours=1)
            description = "Last 1 hour"

        # 2. Day patterns - CRITICAL: all "day" queries should be rolling 24 hours
        elif re.search(r"\b(last|past)\s+(24\s+hours?|1\s+days?|days?)\b", query_lower):
            start_time = end_time - timedelta(days=1)
            description = "Last 24 hours"

        # 3. "Today" - current calendar day only
        elif re.search(r"\btoday\b", query_lower):
            start_time = end_time.replace(hour=0, minute=0, second=0)
            end_time = start_time + timedelta(days=1) - timedelta(seconds=1)
            description = "Today"

        # 4. Week patterns - rolling 7 days
        elif re.search(r"\b(last|past)\s+(7\s+days?|1\s+weeks?|weeks?)\b", query_lower):
            start_time = end_time - timedelta(days=7)
            description = "Last 7 days"

        # 5. "This week" - current calendar week
        elif re.search(r"\bthis\s+week\b", query_lower):
            days_since_monday = end_time.weekday()
            start_time = (end_time - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0
            )
            description = f"This week (since {start_time.strftime('%B %d')})"

        # 6. Month patterns - rolling 30 days (consistent)
        elif re.search(
            r"\b(last|past)\s+(30\s+days?|1\s+months?|months?)\b", query_lower
        ):
            start_time = end_time - timedelta(days=30)
            description = "Last 30 days"

        # 7. "This month" - current calendar month
        elif re.search(r"\bthis\s+month\b", query_lower):
            start_time = end_time.replace(day=1, hour=0, minute=0, second=0)
            description = f"This month ({start_time.strftime('%B %Y')})"

        # 8. Specific numeric patterns
        elif match := re.search(
            r"\b(last|past)\s+(\d+)\s+(hours?|days?|weeks?|months?)\b", query_lower
        ):
            quantity = int(match.group(2))
            unit = match.group(3)

            if "hour" in unit:
                start_time = end_time - timedelta(hours=quantity)
                description = f"Last {quantity} hours"
            elif "day" in unit:
                start_time = end_time - timedelta(days=quantity)
                description = f"Last {quantity} days"
            elif "week" in unit:
                start_time = end_time - timedelta(weeks=quantity)
                description = f"Last {quantity} weeks"
            elif "month" in unit:
                start_time = end_time - timedelta(days=quantity * 30)  # Approximate
                description = f"Last {quantity} months"
            else:
                # Default fallback
                start_time = end_time - timedelta(days=30)
                description = "Last 30 days (default)"
        else:
            # Default: last 30 days
            start_time = end_time - timedelta(days=30)
            description = "Last 30 days (default)"

        # Ensure timezone consistency - remove tzinfo for deterministic behavior
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)

        logger.info(f"Parsed timeframe: {description} ({start_time} to {end_time})")

        return TimeFrame(
            start_date=start_time, end_date=end_time, description=description
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for conversation analysis."""
        return """
        Analyze customer support conversations. Provide 3-5 bullet points sorted by urgency/impact:

        Format each insight as:
        - [CATEGORY] Title (X customers, Y% of total)

          Detailed description with customer examples (email1@domain.com [View](url), email2@domain.com [View](url)).

        Categories: BUG, FEATURE_REQUEST, CONFUSION, COMPLAINT, PROCESS_ISSUE, OTHER

        Sort by: 1) Customer impact (more customers = higher priority), 2) Severity (BUG > COMPLAINT > CONFUSION > FEATURE_REQUEST)

        Add blank lines between insights for readability.
        When referencing customers, include clickable [View] links next to their email addresses.

        End with: "Analyzed X conversations containing Y total messages."
        """

    def _get_followup_system_prompt(self) -> str:
        """Get the system prompt for follow-up question analysis."""
        return """
        Answer the follow-up question about a specific issue from the previous analysis.

        CRITICAL CONSISTENCY RULES:
        - You MUST use the exact same conversation data and customer counts as the previous analysis
        - If the previous analysis said "7 customers" had an issue, you must find and analyze all 7
        - Do NOT re-filter or change the customer count - maintain consistency with previous results
        - Focus only on the specific topic they're asking about, but include ALL customers who had that issue
        - Reference the previous analysis context provided to ensure consistency

        Format: [CATEGORY] Detailed analysis (X customers, consistent with previous)
        Include ALL customer emails that were mentioned in the previous analysis for this issue.

        End with: "Analyzed X customers with this specific issue from cached data."
        """

    def _build_analysis_prompt(
        self, conversations: List[Conversation], query: str
    ) -> str:
        """Build the prompt for conversation analysis."""
        # Filter conversations that have customer interactions
        relevant_conversations = []
        for conv in conversations:
            # Check if conversation has any customer messages
            customer_messages = [m for m in conv.messages if m.author_type == "user"]
            if customer_messages:
                relevant_conversations.append(conv)

        # Compress conversations to fit within token limits while preserving context
        conv_summaries = []
        for conv in relevant_conversations:  # Use all relevant conversations
            customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"

            # Use compression method that preserves context
            compressed = self._compress_conversation(conv, customer_id)
            if compressed:  # Only include if there's meaningful content
                conv_summaries.append(compressed)

        logger.info(
            f"Compressed {len(conv_summaries)} conversations from {len(relevant_conversations)} total"
        )

        # Build conversation mapping for URLs
        conv_mapping = "\n\nConversation URLs for reference:\n"
        for conv in conversations[:50]:
            if self.app_id:
                customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"
                conv_mapping += f"- {customer_id}: {conv.get_url(self.app_id)}\n"

        analysis_prompt = f"""
        Query: {query}

        Analyze these {len(conv_summaries)} customer support conversations:

        {chr(10).join(conv_summaries)}
        """

        if self.app_id:
            analysis_prompt += (
                conv_mapping
                + "\n\nWhen referencing customers in your analysis, include clickable [View] links using the URLs above.\n\n"
            )

        analysis_prompt += "Provide a clear analysis addressing the original query. Remember to mention the total message count at the end."

        return analysis_prompt

    def _calculate_cost(self, usage, model: str = None) -> CostInfo:
        """Calculate the cost of the API call."""
        model_name = model or self.model
        model_costs = self.COSTS.get(model_name, self.COSTS["gpt-4"])

        input_cost = (usage.prompt_tokens / 1000) * model_costs["input"]
        output_cost = (usage.completion_tokens / 1000) * model_costs["output"]
        total_cost = input_cost + output_cost

        return CostInfo(
            tokens_used=usage.total_tokens,
            estimated_cost_usd=total_cost,
            model_used=model_name,
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

    def _compress_conversation(self, conv: Conversation, customer_id: str) -> str:
        """Compress a conversation into a meaningful snippet while preserving context."""
        if not conv.messages:
            return ""

        # Start with conversation header
        summary = f"Conversation from {customer_id} ({conv.created_at.strftime('%Y-%m-%d')}) [ID: {conv.id}]:\n"

        # Find the main customer issue (usually in first few customer messages)
        customer_messages = [m for m in conv.messages if m.author_type == "user"]
        if not customer_messages:
            return ""  # Skip admin-only conversations

        # Get the primary issue from the first customer message
        primary_issue = customer_messages[0].body
        summary += f"  Issue: {primary_issue[:150]}{'...' if len(primary_issue) > 150 else ''}\n"

        # Add key customer responses (yes/no answers, additional details, etc.)
        key_responses = []
        for msg in customer_messages[1:4]:  # Next 3 customer messages
            if msg.body.strip():
                # Even short responses like "yes" or "no" provide context
                response = msg.body.strip()[:100]
                key_responses.append(
                    f"Customer: {response}{'...' if len(msg.body) > 100 else ''}"
                )

        if key_responses:
            summary += "  " + " | ".join(key_responses) + "\n"

        # Add final resolution/status if available from support
        admin_messages = [m for m in conv.messages if m.author_type == "admin"]
        if admin_messages:
            # Look for resolution-indicating messages
            last_admin = admin_messages[-1]
            if any(
                keyword in last_admin.body.lower()
                for keyword in [
                    "resolved",
                    "closed",
                    "fixed",
                    "completed",
                    "solved",
                    "workaround",
                ]
            ):
                resolution = last_admin.body[:100]
                summary += f"  Resolution: {resolution}{'...' if len(last_admin.body) > 100 else ''}\n"

        # Add conversation metadata
        summary += f"  Messages: {len(conv.messages)} | Customer responses: {len(customer_messages)}\n"

        return summary
