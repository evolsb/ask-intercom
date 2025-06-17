"""Main query processing orchestration."""

from time import time

from .ai_client import AIClient
from .config import Config
from .intercom_client import IntercomClient
from .logger import MetricsLogger, get_logger
from .models import AnalysisResult, ConversationFilters

logger = get_logger("query_processor")
metrics = MetricsLogger()


class QueryProcessor:
    """Orchestrates the full query processing workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.intercom_client = IntercomClient(config.intercom_token)
        self.ai_client = AIClient(config.openai_key, config.model)

    async def process_query(self, query: str) -> AnalysisResult:
        """Process a natural language query and return analysis."""
        start_time = time()

        logger.info("Starting query processing", extra={"query_length": len(query)})

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
            intercom_start = time()
            conversations = await self.intercom_client.fetch_conversations(filters)
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
            result = await self.ai_client.analyze_conversations(conversations, query)
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
                f"Query completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
