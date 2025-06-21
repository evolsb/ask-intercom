"""OpenAI integration for conversation analysis."""

import json
import re
from datetime import datetime, timedelta
from typing import List

from openai import AsyncOpenAI

from .logger import get_logger
from .models import (
    AnalysisResult,
    AnalysisSummary,
    Conversation,
    CostInfo,
    CustomerInsight,
    Insight,
    InsightImpact,
    StructuredAnalysisResult,
    TimeFrame,
)

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
        self.fast_model = "gpt-3.5-turbo"  # Faster model for simple queries
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

        # Select optimal model based on query complexity
        selected_model = self._select_model_for_query(query, len(conversations))
        logger.info(
            f"Selected model: {selected_model} for query: '{query[:50]}...' ({len(conversations)} conversations)"
        )

        # Call OpenAI for analysis
        response = await self.client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistent results
            max_tokens=400,  # Efficient response length
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
            description = "today"

        # 4. "Yesterday" - previous calendar day
        elif re.search(r"\byesterday\b", query_lower):
            yesterday = end_time - timedelta(days=1)
            start_time = yesterday.replace(hour=0, minute=0, second=0)
            end_time = start_time + timedelta(days=1) - timedelta(seconds=1)
            description = "yesterday"

        # 5. Week patterns - rolling 7 days
        elif re.search(r"\b(last|past)\s+(7\s+days?|1\s+weeks?|weeks?)\b", query_lower):
            start_time = end_time - timedelta(days=7)
            description = "Last 7 days"

        # 6. "This week" - current calendar week
        elif re.search(r"\bthis\s+week\b", query_lower):
            days_since_monday = end_time.weekday()
            start_time = (end_time - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0
            )
            description = f"this week (since {start_time.strftime('%B %d')})"

        # 7. Month patterns - rolling 30 days (consistent)
        elif re.search(
            r"\b(last|past)\s+(30\s+days?|1\s+months?|months?)\b", query_lower
        ):
            start_time = end_time - timedelta(days=30)
            description = "Last 30 days"

        # 8. "This month" - current calendar month
        elif re.search(r"\bthis\s+month\b", query_lower):
            start_time = end_time.replace(day=1, hour=0, minute=0, second=0)
            description = f"this month ({start_time.strftime('%B %Y')})"

        # 9. Specific numeric patterns
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

    async def analyze_conversations_structured(
        self, conversations: List[Conversation], query: str, timeframe: TimeFrame
    ) -> StructuredAnalysisResult:
        """Analyze conversations and generate structured JSON insights."""
        # Build the analysis prompt
        prompt = self._build_structured_analysis_prompt(conversations, query)

        # JSON schema for the response (currently unused but kept for future validation)
        _json_schema = {
            "type": "object",
            "properties": {
                "insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": [
                                    "BUG",
                                    "FEATURE_REQUEST",
                                    "COMPLAINT",
                                    "PRAISE",
                                    "QUESTION",
                                    "OTHER",
                                ],
                            },
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "impact": {
                                "type": "object",
                                "properties": {
                                    "customer_count": {"type": "integer"},
                                    "percentage": {"type": "number"},
                                    "severity": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high", "critical"],
                                    },
                                },
                                "required": [
                                    "customer_count",
                                    "percentage",
                                    "severity",
                                ],
                            },
                            "customers": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "email": {"type": "string"},
                                        "conversation_id": {"type": "string"},
                                        "intercom_url": {"type": "string"},
                                        "issue_summary": {"type": "string"},
                                    },
                                    "required": [
                                        "email",
                                        "conversation_id",
                                        "intercom_url",
                                        "issue_summary",
                                    ],
                                },
                            },
                            "priority_score": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "recommendation": {"type": "string"},
                        },
                        "required": [
                            "id",
                            "category",
                            "title",
                            "description",
                            "impact",
                            "customers",
                            "priority_score",
                            "recommendation",
                        ],
                    },
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_conversations": {"type": "integer"},
                        "total_messages": {"type": "integer"},
                        "analysis_timestamp": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "total_conversations",
                        "total_messages",
                        "analysis_timestamp",
                    ],
                },
            },
            "required": ["insights", "summary"],
        }

        # Call OpenAI for analysis with JSON response format
        # Note: json_object response format requires gpt-4-turbo or newer
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Use turbo for JSON mode support
            messages=[
                {"role": "system", "content": self._get_structured_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistent results
            response_format={"type": "json_object"},
            max_tokens=2000,  # More tokens for structured output
        )

        # Parse JSON response
        try:
            raw_content = response.choices[0].message.content

            # Clean up common JSON issues
            cleaned_content = self._cleanup_json_response(raw_content)
            response_json = json.loads(cleaned_content)

            # Convert to dataclass objects
            insights = []
            for insight_data in response_json["insights"]:
                customers = [
                    CustomerInsight(**customer)
                    for customer in insight_data["customers"]
                ]

                impact = InsightImpact(**insight_data["impact"])

                insight = Insight(
                    id=insight_data["id"],
                    category=insight_data["category"],
                    title=insight_data["title"],
                    description=insight_data["description"],
                    impact=impact,
                    customers=customers,
                    priority_score=insight_data["priority_score"],
                    recommendation=insight_data["recommendation"],
                )
                insights.append(insight)

            # Parse summary
            summary_data = response_json["summary"]
            summary = AnalysisSummary(
                total_conversations=summary_data["total_conversations"],
                total_messages=summary_data["total_messages"],
                analysis_timestamp=datetime.fromisoformat(
                    summary_data["analysis_timestamp"].replace("Z", "+00:00")
                ),
            )

            return StructuredAnalysisResult(insights=insights, summary=summary)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse structured response: {e}")
            logger.error(
                f"Raw response content (first 500 chars): {raw_content[:500]}..."
            )
            logger.error(
                f"Raw response content (last 500 chars): ...{raw_content[-500:]}"
            )
            logger.error(f"Total response length: {len(raw_content)} characters")

            # Save full response for debugging
            import tempfile

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".json", prefix="failed_response_"
                ) as f:
                    f.write(raw_content)
                    logger.error(f"Full response saved to: {f.name}")
            except Exception as save_error:
                logger.error(f"Could not save response for debugging: {save_error}")

            raise ValueError(f"Failed to parse AI response: {e}") from e

    def _cleanup_json_response(self, content: str) -> str:
        """Clean up common JSON formatting issues from AI responses."""
        if not content:
            return content

        # Remove any leading/trailing whitespace
        content = content.strip()

        # Remove code block markers if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        # Handle unterminated strings by finding the last valid JSON
        try:
            # Try to parse as-is first
            json.loads(content)
            return content
        except json.JSONDecodeError as e:
            # If it's an unterminated string, try to fix it
            if "Unterminated string" in str(e):
                # Extract line number from error message
                import re

                line_match = re.search(r"line (\d+)", str(e))
                error_line = int(line_match.group(1)) if line_match else 100

                lines = content.split("\n")
                logger.info(f"Attempting JSON recovery from error at line {error_line}")

                # Try truncating at various points before the error
                for offset in [1, 2, 5, 10, 20]:
                    truncate_line = max(1, error_line - offset)
                    if truncate_line < len(lines):
                        truncated = "\n".join(lines[:truncate_line])

                        # Close open braces/brackets
                        open_braces = truncated.count("{") - truncated.count("}")
                        open_brackets = truncated.count("[") - truncated.count("]")

                        if open_braces > 0:
                            truncated += "}" * open_braces
                        if open_brackets > 0:
                            truncated += "]" * open_brackets

                        try:
                            json.loads(truncated)  # Validate JSON is parseable
                            logger.info(
                                f"JSON recovery successful at line {truncate_line}"
                            )
                            return truncated
                        except json.JSONDecodeError as parse_error:
                            logger.debug(
                                f"Recovery attempt at line {truncate_line} failed: {parse_error}"
                            )
                            continue

            # If we can't fix it, return original
            return content

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

    def _select_model_for_query(self, query: str, conversation_count: int) -> str:
        """Select optimal model based on query complexity."""
        import re

        query_lower = query.lower()

        # Simple queries → faster model
        simple_patterns = [
            r"\bhow many\b",
            r"\bcount\b",
            r"\blist\b",
            r"\bshow me\b",
            r"\bwhat are\b",
        ]

        # Complex analysis → GPT-4
        complex_patterns = [
            r"\banalyze\b",
            r"\bcompare\b",
            r"\bexplain why\b",
            r"\broot cause\b",
            r"\bpatterns\b",
            r"\btrends\b",
        ]

        # Small datasets → faster model
        if conversation_count <= 20:
            return self.fast_model

        # Complex queries → main model
        if any(re.search(pattern, query_lower) for pattern in complex_patterns):
            return self.model

        # Simple queries → fast model
        if any(re.search(pattern, query_lower) for pattern in simple_patterns):
            return self.fast_model

        # Default → main model
        return self.model

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

    def _get_structured_system_prompt(self) -> str:
        """Get the system prompt for structured JSON conversation analysis."""
        return """
        You are an expert customer support analyst. Analyze conversations and provide insights in JSON format.

        CRITICAL INSTRUCTIONS:
        1. Return ONLY valid JSON - no markdown, no explanations
        2. Categorize each insight appropriately (BUG, FEATURE_REQUEST, COMPLAINT, PRAISE, QUESTION, OTHER)
        3. Calculate accurate customer counts and percentages
        4. Assign priority scores (0-100) based on impact and severity
        5. Include ALL affected customers with their details
        6. Provide actionable recommendations

        Priority scoring guidelines:
        - Critical bugs affecting many users: 90-100
        - Major complaints or widespread issues: 70-89
        - Feature requests with high demand: 50-69
        - Minor issues or questions: 30-49
        - Low impact items: 0-29

        Severity levels:
        - critical: Business-critical issues, data loss, security
        - high: Major functionality broken, blocking workflows
        - medium: Significant inconvenience, workarounds available
        - low: Minor issues, cosmetic problems
        """

    def _build_structured_analysis_prompt(
        self, conversations: List[Conversation], query: str
    ) -> str:
        """Build the prompt for structured conversation analysis."""
        # Get conversation data
        conv_data = []
        total_messages = 0

        for conv in conversations:
            customer_messages = [m for m in conv.messages if m.author_type == "user"]
            if not customer_messages:
                continue

            total_messages += len(conv.messages)

            conv_info = {
                "conversation_id": conv.id,
                "customer_email": conv.customer_email or f"anonymous-{conv.id[:8]}",
                "url": conv.get_url(self.app_id)
                if self.app_id
                else f"https://app.intercom.com/conversation/{conv.id}",
                "messages": [],
            }

            # Include key messages
            for msg in customer_messages[:3]:  # First 3 customer messages
                conv_info["messages"].append(
                    {
                        "type": "customer",
                        "content": msg.body[:200]
                        + ("..." if len(msg.body) > 200 else ""),
                    }
                )

            # Include last admin response if exists
            admin_messages = [m for m in conv.messages if m.author_type == "admin"]
            if admin_messages:
                last_admin = admin_messages[-1]
                conv_info["messages"].append(
                    {
                        "type": "admin",
                        "content": last_admin.body[:200]
                        + ("..." if len(last_admin.body) > 200 else ""),
                    }
                )

            conv_data.append(conv_info)

        analysis_prompt = f"""
        Query: {query}

        Analyze these {len(conv_data)} conversations and provide structured insights.

        Conversation data:
        {json.dumps(conv_data, indent=2)}

        Return a JSON object with:
        1. "insights": Array of insight objects, each with:
           - id: unique identifier (e.g., "insight_1")
           - category: BUG, FEATURE_REQUEST, COMPLAINT, PRAISE, QUESTION, or OTHER
           - title: Brief, clear title
           - description: Detailed explanation
           - impact: object with customer_count, percentage, and severity
           - customers: array of affected customers with email, conversation_id, intercom_url, and issue_summary
           - priority_score: 0-100 based on impact
           - recommendation: Actionable next step

        2. "summary": Object with:
           - total_conversations: {len(conversations)}
           - total_messages: {total_messages}
           - analysis_timestamp: Current ISO timestamp

        Group similar issues together and sort by priority_score descending.
        """

        return analysis_prompt
