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
            model=self.timeframe_model,
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

        # Count total messages (before filtering)
        total_messages = sum(len(conv.messages) for conv in relevant_conversations)

        # Count filtered messages
        filtered_messages = 0

        # Summarize conversations to fit within token limits
        conv_summaries = []
        for conv in relevant_conversations[:50]:  # Limit to prevent token overflow
            customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"
            summary = f"Conversation from {customer_id} ({conv.created_at.strftime('%Y-%m-%d')}) [ID: {conv.id}]:\n"

            # Filter and include only meaningful messages
            message_count = 0
            for msg in conv.messages[:10]:  # Increased limit to see more context
                # Skip very short messages
                if len(msg.body.strip()) < 10:
                    filtered_messages += 1
                    continue

                # Skip common auto-responses and boilerplate
                lower_body = msg.body.lower().strip()
                if any(
                    pattern in lower_body
                    for pattern in [
                        "this conversation has been closed",
                        "conversation was closed automatically",
                        "thanks for contacting",
                        "we'll get back to you",
                        "your request has been received",
                        "ticket has been created",
                        "this is an automated message",
                        "do not reply to this email",
                        "case has been escalated",
                        "merged with another conversation",
                    ]
                ):
                    filtered_messages += 1
                    continue

                # Skip admin-only messages if no customer response follows
                if msg.author_type == "admin":
                    # Check if there's a customer message after this
                    msg_index = conv.messages.index(msg)
                    has_customer_response = any(
                        m.author_type == "user" for m in conv.messages[msg_index + 1 :]
                    )
                    if not has_customer_response and message_count > 0:
                        filtered_messages += 1
                        continue
                author = "Customer" if msg.author_type == "user" else "Support"
                summary += f"  {author}: {msg.body[:200]}...\n"
                message_count += 1

                if message_count >= 5:  # Limit messages shown per conversation
                    break

            if message_count > 0:  # Only include conversations with meaningful content
                conv_summaries.append(summary)

        actual_messages = total_messages - filtered_messages
        logger.info(
            f"Filtered {filtered_messages} low-value messages from {total_messages} total"
        )

        # Build conversation mapping for URLs
        conv_mapping = "\n\nConversation URLs for reference:\n"
        for conv in conversations[:50]:
            if self.app_id:
                customer_id = conv.customer_email or f"anonymous-{conv.id[:8]}"
                conv_mapping += f"- {customer_id}: {conv.get_url(self.app_id)}\n"

        analysis_prompt = f"""
        Query: {query}

        Analyze these {len(relevant_conversations)} customer support conversations (containing {actual_messages} meaningful messages after filtering):

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
