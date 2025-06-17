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
                limit=self.config.max_conversations,
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
                    cost_info=CostInfo(
                        tokens_used=0,
                        estimated_cost_usd=0.0,
                        model_used=self.config.model,
                    ),
                )

            # Step 3: Analyze conversations with AI
            logger.info(f"Analyzing {len(conversations)} conversations...")
            result = await self.ai_client.analyze_conversations(conversations, query)

            # Log performance
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Query completed in {duration:.1f}s, cost: ${result.cost_info.estimated_cost_usd:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
