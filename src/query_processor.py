"""Main query processing orchestration."""

import asyncio
from time import time

import httpx

from .ai_client import AIClient
from .config import Config
from .intercom_client import IntercomClient
from .logger import MetricsLogger, get_logger, get_request_context
from .models import (
    AnalysisResult,
    ConversationFilters,
    CostInfo,
    SessionState,
    StructuredAnalysisResult,
    TimeFrame,
)

logger = get_logger("query_processor")
metrics = MetricsLogger()


class QueryProcessor:
    """Orchestrates the full query processing workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.intercom_client = IntercomClient(config.intercom_token)
        # AI client will be initialized with app_id during query processing
        self.ai_client = None
        self._last_structured_result = None
        self._last_conversations = None

    def _estimate_processing_time(self, conversation_count: int) -> float:
        """Estimate processing time based on conversation count."""
        # Based on observed performance:
        # - API fetch: ~0.15s per conversation (batched)
        # - AI analysis: ~0.3s per conversation
        # - Base overhead: ~5s
        fetch_time = min(conversation_count * 0.02, 10)  # Batched fetching
        analysis_time = conversation_count * 0.3
        overhead = 5
        return fetch_time + analysis_time + overhead

    def _estimate_processing_cost(self, conversation_count: int) -> float:
        """Estimate OpenAI API cost based on conversation count."""
        # Based on observed costs:
        # - ~$0.004 per conversation for GPT-4
        # - Includes both analysis and timeframe interpretation
        cost_per_conversation = 0.004
        base_cost = 0.01  # Timeframe interpretation
        return base_cost + (conversation_count * cost_per_conversation)

    async def count_conversations_for_query(self, query: str) -> tuple[int, TimeFrame]:
        """Preview how many conversations would be analyzed for a query."""
        # Initialize AI client if needed
        if not self.ai_client:
            app_id = await self.intercom_client.get_app_id()
            self.ai_client = AIClient(
                self.config.openai_key, self.config.model, app_id, "gpt-3.5-turbo"
            )

        # Interpret timeframe
        timeframe = await self.ai_client._interpret_timeframe(query)

        # Create a filters object with high limit just to count
        from .models import ConversationFilters

        filters = ConversationFilters(
            start_date=timeframe.start_date,
            end_date=timeframe.end_date,
            limit=10000,  # High limit to get true count
        )

        # Quick count - just fetch first page to get total
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_query = {
                "query": {
                    "operator": "AND",
                    "value": [
                        {
                            "field": "created_at",
                            "operator": ">",
                            "value": int(filters.start_date.timestamp()),
                        },
                        {
                            "field": "created_at",
                            "operator": "<",
                            "value": int(filters.end_date.timestamp()),
                        },
                    ],
                },
                "pagination": {"per_page": 1},  # Just need count
            }

            response = await client.post(
                f"{self.intercom_client.base_url}/conversations/search",
                headers=self.intercom_client.headers,
                json=search_query,
            )
            response.raise_for_status()
            data = response.json()

            total_count = data.get("total_count", 0)
            return total_count, timeframe

    async def process_query(
        self, query: str, session: SessionState = None, progress_callback=None
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

        # Report initial progress
        if progress_callback:
            await progress_callback("starting", "Initializing query processor...", 0)

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
            # Step 0: Initialize AI client with dynamically fetched app ID
            if not self.ai_client:
                if progress_callback:
                    await progress_callback(
                        "initializing", "Fetching Intercom app configuration...", 5
                    )
                logger.info("Fetching Intercom app ID for conversation links...")
                app_id = await self.intercom_client.get_app_id()
                if app_id:
                    logger.info(f"Using app ID: {app_id}")
                else:
                    logger.info("No app ID found - conversation links will be disabled")
                self.ai_client = AIClient(
                    self.config.openai_key, self.config.model, app_id, "gpt-3.5-turbo"
                )

            # Step 1: Interpret timeframe from query
            if progress_callback:
                await progress_callback(
                    "timeframe", "Interpreting query timeframe...", 10
                )
            logger.info("Interpreting query timeframe...")
            timeframe_start = time()
            timeframe = await self.ai_client._interpret_timeframe(query)
            metrics.log_api_call("openai_timeframe", time() - timeframe_start, True)

            # Step 2: Fetch relevant conversations
            if progress_callback:
                await progress_callback(
                    "fetching",
                    f"Fetching conversations from {timeframe.description}...",
                    20,
                )
            logger.info(f"Fetching conversations from {timeframe.description}...")

            # Use simple conversation limit - respect user configuration
            max_conversations = self.config.max_conversations
            if max_conversations is not None and max_conversations > 1000:
                max_conversations = 1000
                logger.info(
                    f"Conversation limit capped at 1000 (requested: {self.config.max_conversations})"
                )
                print(
                    f"📊 Conversation limit capped at 1000 (requested: {self.config.max_conversations})"
                )
            elif max_conversations is None:
                logger.info(f"No conversation limit set for {timeframe.description}")
            else:
                logger.info(
                    f"Using limit of {max_conversations} conversations for {timeframe.description}"
                )

            filters = ConversationFilters(
                start_date=timeframe.start_date,
                end_date=timeframe.end_date,
                limit=max_conversations,
            )

            # Start fetching conversations and analyzing in parallel
            intercom_start = time()
            logger.info(f"🚀 Starting data fetch at {intercom_start:.3f}s")
            fetch_task = asyncio.create_task(
                self.intercom_client.fetch_conversations(filters, progress_callback)
            )

            # Wait for conversations to be fetched
            conversations = await fetch_task
            fetch_duration_seconds = time() - intercom_start
            fetch_duration_ms = fetch_duration_seconds * 1000
            logger.info(f"📊 Data fetch completed: {fetch_duration_ms:.1f}ms for {len(conversations)} conversations")
            metrics.log_api_call("intercom", fetch_duration_seconds, True)

            # Store conversations for session persistence
            self._last_conversations = conversations

            # Report fetch completion with conversation count
            if progress_callback:
                await progress_callback(
                    "fetching",
                    f"Found {len(conversations)} conversations to analyze",
                    50,
                )

            if not conversations:
                # Return empty result if no conversations found
                from .models import CostInfo

                return AnalysisResult(
                    summary="No conversations found in the specified timeframe.",
                    key_insights=[],
                    conversation_count=0,
                    time_range=timeframe,
                    cost_info=CostInfo.zero_cost(self.config.model),
                )

            # Estimate processing metrics
            conversation_count = len(conversations)
            estimated_time_seconds = self._estimate_processing_time(conversation_count)
            estimated_cost = self._estimate_processing_cost(conversation_count)

            # Log warning if large dataset
            if conversation_count > 100:
                logger.warning(
                    f"Large dataset detected: {conversation_count} conversations. "
                    f"Estimated time: {estimated_time_seconds:.1f}s, cost: ${estimated_cost:.2f}"
                )
                print(
                    f"\n⚠️  Found {conversation_count} conversations to analyze\n"
                    f"📊 Estimated processing time: {estimated_time_seconds:.1f} seconds\n"
                    f"💰 Estimated cost: ${estimated_cost:.2f}\n"
                )

            # Step 3: Analyze conversations with AI
            if progress_callback:
                await progress_callback(
                    "analyzing",
                    f"Analyzing {len(conversations)} conversations with AI...",
                    75,
                )
            logger.info(f"Analyzing {len(conversations)} conversations...")
            print(
                f"\r🧠 Analyzing {len(conversations)} conversations...",
                end="",
                flush=True,
            )
            analysis_start = time()
            logger.info(f"🧠 Starting AI analysis at {analysis_start:.3f}s")

            # Try structured analysis first, fall back to legacy if needed
            try:
                logger.info(f"🎯 Attempting structured JSON analysis for {len(conversations)} conversations")
                if progress_callback:
                    await progress_callback(
                        "analyzing",
                        f"Generating structured insights with {self.config.model}...",
                        80,
                    )

                structured_result = (
                    await self.ai_client.analyze_conversations_structured(
                        conversations, query, timeframe
                    )
                )

                if progress_callback:
                    await progress_callback(
                        "analyzing",
                        "✨ AI analysis complete, formatting results...",
                        90,
                    )

                # Convert structured result to legacy format for now
                # TODO: Update frontend to use structured format directly
                result = self._convert_structured_to_legacy(
                    structured_result, timeframe
                )
                logger.info("✅ Successfully used structured analysis")
                # Store structured result for web API access
                self._last_structured_result = structured_result
            except Exception as e:
                logger.warning(
                    f"❌ Structured analysis failed, falling back to legacy: {e}"
                )
                if progress_callback:
                    await progress_callback(
                        "analyzing",
                        "Falling back to legacy analysis...",
                        80,
                    )
                result = await self.ai_client.analyze_conversations(
                    conversations, query, timeframe
                )
                self._last_structured_result = None

            analysis_duration_seconds = time() - analysis_start
            analysis_duration_ms = analysis_duration_seconds * 1000
            logger.info(f"⚡ AI analysis completed: {analysis_duration_ms:.1f}ms")
            metrics.log_api_call("openai_analysis", analysis_duration_seconds, True)
            print(f"\r✅ Analysis complete ({analysis_duration_seconds:.1f}s)          ")

            # Add timing information to result
            total_processing_ms = (time() - start_time) * 1000
            result.processing_time_ms = total_processing_ms
            result.fetch_time_ms = fetch_duration_ms
            result.analysis_time_ms = analysis_duration_ms

            # Report analysis completion
            if progress_callback:
                await progress_callback("finalizing", "Saving analysis results...", 95)

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

            print(
                f"\r✨ Query completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}    ",
                flush=True,
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
            duration = time() - start_time
            print(f"\r❌ Error after {duration:.1f}s: {str(e)}          ", flush=True)
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

        # Initialize AI client if not already done
        if not self.ai_client:
            logger.info("Initializing AI client for follow-up analysis...")
            print("\r🔗 Initializing AI client...", end="", flush=True)
            app_id = await self.intercom_client.get_app_id()
            self.ai_client = AIClient(
                self.config.openai_key, self.config.model, app_id, "gpt-3.5-turbo"
            )
            print("\r✅ AI client ready               ")

        # Use cached conversations for follow-up analysis
        conversations = session.last_conversations
        timeframe = session.last_timeframe

        logger.info(
            f"Processing follow-up on {len(conversations)} cached conversations"
        )

        # Note: Previous analysis context is now handled in the conversational AI method

        # Analyze with the follow-up context using conversational response
        print(
            f"\r🔍 Processing conversational follow-up for {len(conversations)} conversations...",
            end="",
            flush=True,
        )
        analysis_start = time()

        # Use the new conversational follow-up method
        conversational_response = await self.ai_client.analyze_conversations_followup(
            conversations, query, timeframe
        )

        # Create a simplified result structure for follow-ups
        from src.models import CostInfo

        # Create estimated cost info for follow-up (we'll track this properly later)
        cost_info = CostInfo.from_usage(
            usage_tokens=1800,  # Estimate: ~1000 input + 800 output
            model="gpt-4-turbo-preview",
            cost_per_token=0.00003,  # Rough estimate
        )

        # Create a conversational analysis result
        result = AnalysisResult(
            summary=conversational_response,  # Free-text conversational response
            key_insights=[conversational_response],  # Simple format for now
            conversation_count=len(conversations),
            time_range=timeframe,
            cost_info=cost_info,
        )

        metrics.log_api_call("openai_followup", time() - analysis_start, True)
        followup_duration = time() - analysis_start
        print(f"\r✅ Conversational follow-up complete ({followup_duration:.1f}s)    ")

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

        print(
            f"\r✨ AI follow-up completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}    ",
            flush=True,
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

    def _convert_structured_to_legacy(
        self, structured: StructuredAnalysisResult, timeframe: TimeFrame
    ) -> AnalysisResult:
        """Convert structured analysis result to legacy format."""
        # Build markdown summary from structured insights
        summary_parts = []

        for insight in structured.insights:
            # Format: [CATEGORY] Title (X customers, Y%)
            header = f"[{insight.category}] {insight.title} ({insight.impact.customer_count} customers, {insight.impact.percentage:.1f}% of total)\n"

            # Description with customer examples
            customer_examples = []
            for customer in insight.customers[:3]:  # Show first 3 customers
                customer_examples.append(
                    f"{customer.email} [View]({customer.intercom_url})"
                )

            if len(insight.customers) > 3:
                customer_examples.append(f"and {len(insight.customers) - 3} more...")

            description = (
                f"{insight.description} Examples: {', '.join(customer_examples)}.\n"
            )

            summary_parts.append(header + "\n" + description)

        # Add final summary line
        summary_parts.append(
            f"\nAnalyzed {structured.summary.total_conversations} conversations "
            f"containing {structured.summary.total_messages} total messages."
        )

        summary = "\n".join(summary_parts)

        # Extract key insights (titles only)
        key_insights = [insight.title for insight in structured.insights[:5]]

        # Calculate cost info (approximate based on summary length)
        tokens_used = len(summary) // 4  # Rough approximation
        cost_info = CostInfo.from_usage(usage_tokens=tokens_used, model="gpt-4")

        return AnalysisResult(
            summary=summary,
            key_insights=key_insights,
            conversation_count=structured.summary.total_conversations,
            time_range=timeframe,
            cost_info=cost_info,
        )

    def get_last_structured_result(self) -> StructuredAnalysisResult:
        """Get the last structured analysis result if available."""
        return self._last_structured_result
