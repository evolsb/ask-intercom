"""Main query processing orchestration."""

import asyncio
from time import time

from .ai_client import AIClient
from .config import Config
from .intercom_client import IntercomClient
from .logger import MetricsLogger, get_logger, get_request_context
from .models import AnalysisResult, ConversationFilters, SessionState

logger = get_logger("query_processor")
metrics = MetricsLogger()


class QueryProcessor:
    """Orchestrates the full query processing workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.intercom_client = IntercomClient(config.intercom_token)
        self.ai_client = AIClient(config.openai_key, config.model)

    async def process_query(
        self, query: str, session: SessionState = None
    ) -> AnalysisResult:
        """Process a natural language query and return analysis."""
        start_time = time()

        # Get session context for logging
        request_context = get_request_context()

        logger.info(
            "Starting query processing",
            extra={
                "query_length": len(query),
                "session_id": request_context,
                "query_preview": query[:50] + "..." if len(query) > 50 else query,
            },
        )

        # Check if this is a follow-up question
        if session and session.last_conversations and self._is_followup_question(query):
            logger.info(
                "Detected follow-up question, using cached conversations",
                extra={
                    "cached_conversations": len(session.last_conversations),
                    "followup_type": "cached_analysis",
                },
            )
            return await self._process_followup(query, session)

        try:
            # Step 1: Interpret timeframe from query
            logger.info("Interpreting query timeframe...")
            timeframe_start = time()
            timeframe = await self.ai_client._interpret_timeframe(query)
            metrics.log_api_call("openai_timeframe", time() - timeframe_start, True)

            # Step 2: Fetch relevant conversations
            logger.info(f"Fetching conversations from {timeframe.description}...")
            filters = ConversationFilters(
                start_date=timeframe.start_date,
                end_date=timeframe.end_date,
                limit=self.config.max_conversations,
            )

            # Start fetching conversations and analyzing in parallel
            intercom_start = time()
            fetch_task = asyncio.create_task(
                self.intercom_client.fetch_conversations(filters)
            )

            # Wait for conversations to be fetched
            conversations = await fetch_task
            metrics.log_api_call("intercom", time() - intercom_start, True)

            if not conversations:
                # Return empty result if no conversations found
                from .models import CostInfo

                return AnalysisResult(
                    summary="No conversations found in the specified timeframe.",
                    key_insights=[],
                    conversation_count=0,
                    time_range=timeframe,
                    cost_info=CostInfo(
                        tokens_used=0,
                        estimated_cost_usd=0.0,
                        model_used=self.config.model,
                    ),
                )

            # Step 3: Analyze conversations with AI
            logger.info(f"Analyzing {len(conversations)} conversations...")
            analysis_start = time()
            result = await self.ai_client.analyze_conversations(
                conversations, query, timeframe
            )
            metrics.log_api_call("openai_analysis", time() - analysis_start, True)

            # Log performance metrics
            duration = time() - start_time
            metrics.log_query_performance(
                query=query,
                duration=duration,
                conversation_count=result.conversation_count,
                tokens_used=result.cost_info.tokens_used,
                cost_usd=result.cost_info.estimated_cost_usd,
                model=result.cost_info.model_used,
            )

            # Log cost warning if expensive
            if result.cost_info.estimated_cost_usd > 0.50:
                metrics.log_cost_warning(
                    result.cost_info.tokens_used,
                    result.cost_info.estimated_cost_usd,
                    0.50,
                )

            logger.info(
                f"Query completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}",
                extra={
                    "session_id": request_context,
                    "duration_seconds": duration,
                    "cost_usd": result.cost_info.estimated_cost_usd,
                    "conversations_analyzed": result.conversation_count,
                    "response_type": "full_analysis",
                },
            )

            # Update session state if provided
            if session:
                session.last_query = query
                session.last_conversations = conversations
                session.last_analysis = result
                session.last_timeframe = timeframe

            return result

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise

    def _is_followup_question(self, query: str) -> bool:
        """Detect if a query is a follow-up question about previous results."""
        query_lower = query.lower()
        followup_patterns = [
            "tell me more about",
            "more details on",
            "explain the",
            "what about",
            "drill into",
            "elaborate on",
            "expand on",
            "show me more",
            "details about",
            "specifics on",
            "verification",  # Specific to common issues
            "access to funds",
            "business account",
            "onboarding",
        ]

        return any(pattern in query_lower for pattern in followup_patterns)

    async def _process_followup(
        self, query: str, session: SessionState
    ) -> AnalysisResult:
        """Process a follow-up question using cached conversation data."""
        start_time = time()
        request_context = get_request_context()

        # Use cached conversations for follow-up analysis
        conversations = session.last_conversations
        timeframe = session.last_timeframe

        logger.info(
            f"Processing follow-up on {len(conversations)} cached conversations"
        )

        # Create a follow-up specific prompt that filters conversations
        followup_prompt = f"""
        Answer this specific follow-up question: {query}

        IMPORTANT: Only analyze conversations and messages that are directly related to what the user is asking about.
        Ignore all other issues, complaints, or topics that don't match the follow-up question.

        If the user asks about "verification issues", only show verification-related problems.
        If they ask about "access to funds", only show fund access problems.
        If they ask about "business accounts", only show business account requests.

        Provide 2-3 focused bullet points maximum, only about the specific topic they're asking about.
        Include customer examples and specific details from relevant conversations only.
        """

        # Analyze with the follow-up context
        analysis_start = time()
        result = await self.ai_client.analyze_conversations(
            conversations, followup_prompt, timeframe
        )
        metrics.log_api_call("openai_followup", time() - analysis_start, True)

        # Log metrics
        duration = time() - start_time
        metrics.log_query_performance(
            query=f"FOLLOWUP: {query}",
            duration=duration,
            conversation_count=result.conversation_count,
            tokens_used=result.cost_info.tokens_used,
            cost_usd=result.cost_info.estimated_cost_usd,
            model=result.cost_info.model_used,
        )

        logger.info(
            f"Follow-up completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}",
            extra={
                "session_id": request_context,
                "duration_seconds": duration,
                "cost_usd": result.cost_info.estimated_cost_usd,
                "conversations_analyzed": result.conversation_count,
                "response_type": "followup_analysis",
            },
        )

        return result
