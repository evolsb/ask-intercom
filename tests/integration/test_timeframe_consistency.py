#!/usr/bin/env python3
"""
Integration test for timeframe consistency.

Tests that different phrasings for the same time period return identical results.
This ensures the AI timeframe interpretation is consistent and deterministic.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Tuple

from src.config import Config
from src.query_processor import QueryProcessor

# Set up verbose logging for the test with real-time output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,  # Ensure output goes to stdout for real-time visibility
    force=True,  # Override any existing logging config
)


# Ensure logs are flushed immediately
def flush_logs():
    sys.stdout.flush()
    sys.stderr.flush()


class TimeframeConsistencyTest:
    """Test timeframe consistency across different query phrasings."""

    def __init__(self):
        self.config = Config.from_env()
        # Temporarily increase limits for thorough testing
        self.config.max_conversations = 200  # Higher limit to see true patterns
        self.processor = QueryProcessor(self.config)
        self.results = {}

    async def test_equivalent_timeframes(self) -> bool:
        """Test that equivalent timeframe expressions return identical results."""
        print("🔍 Testing timeframe consistency...")
        print("=" * 60)

        # Define test cases: equivalent expressions for the same time periods
        test_cases = [
            # 1 hour
            {
                "period": "1 hour",
                "queries": [
                    "Show me issues from the last 1 hour",
                    "Show me issues from the past hour",
                ],
            },
            # 24 hours vs 1 day
            {
                "period": "24 hours / 1 day",
                "queries": [
                    "Show me issues from the last 24 hours",
                    "Show me issues from the last 1 day",
                    "Show me issues from the past day",
                ],
            },
            # 7 days vs 1 week
            {
                "period": "7 days / 1 week",
                "queries": [
                    "Show me issues from the last 7 days",
                    "Show me issues from the last 1 week",
                    "Show me issues from the past week",
                ],
            },
            # 30 days vs 1 month
            {
                "period": "30 days / 1 month",
                "queries": [
                    "Show me issues from the last 30 days",
                    "Show me issues from the last 1 month",
                    "Show me issues from the past month",
                ],
            },
        ]

        all_passed = True
        results_by_period = {}

        for test_case in test_cases:
            print(f"\n📅 Testing: {test_case['period']}")
            print("-" * 40)

            success, period_results = await self._test_query_group(
                test_case["queries"], test_case["period"]
            )
            results_by_period[test_case["period"]] = period_results
            if not success:
                all_passed = False

        # Test containment relationships
        print("\n🔗 Testing containment relationships...")
        print("-" * 40)
        containment_success = await self._test_containment_relationships(
            results_by_period
        )
        if not containment_success:
            all_passed = False

        return all_passed

    async def _test_query_group(
        self, queries: List[str], period_name: str
    ) -> Tuple[bool, List[Dict]]:
        """Test a group of equivalent queries and compare results."""
        results = []
        timeframes = []

        print(f"🔍 Testing {len(queries)} equivalent expressions for {period_name}")

        # Run each query and collect results
        for i, query in enumerate(queries):
            print(f"  {i+1}. Testing: '{query}'")

            try:
                # Extract just the timeframe interpretation (without full analysis)
                timeframe = (
                    await self.processor.ai_client._interpret_timeframe(query)
                    if self.processor.ai_client
                    else None
                )

                if not timeframe:
                    print("     🔧 Initializing AI client...")
                    # Initialize AI client if needed
                    app_id = await self.processor.intercom_client.get_app_id()
                    from src.ai_client import AIClient

                    self.processor.ai_client = AIClient(
                        self.config.openai_key,
                        self.config.model,
                        app_id,
                        "gpt-3.5-turbo",
                    )
                    timeframe = await self.processor.ai_client._interpret_timeframe(
                        query
                    )

                print(f"     🕐 Timeframe: {timeframe.description}")
                print(
                    f"     📅 Range: {timeframe.start_date.strftime('%Y-%m-%d %H:%M')} to {timeframe.end_date.strftime('%Y-%m-%d %H:%M')}"
                )
                print(
                    f"     ⏱️  Duration: {(timeframe.end_date - timeframe.start_date).total_seconds() / 3600:.1f} hours"
                )

                # Get actual conversation count for this timeframe
                print("     🔍 Fetching conversations...")
                flush_logs()  # Ensure progress is visible

                from src.models import ConversationFilters

                filters = ConversationFilters(
                    start_date=timeframe.start_date,
                    end_date=timeframe.end_date,
                    limit=self.config.max_conversations,
                )

                conversations = (
                    await self.processor.intercom_client.fetch_conversations(filters)
                )

                result_data = {
                    "query": query,
                    "timeframe": {
                        "start_date": timeframe.start_date.isoformat(),
                        "end_date": timeframe.end_date.isoformat(),
                        "description": timeframe.description,
                        "duration_hours": (
                            timeframe.end_date - timeframe.start_date
                        ).total_seconds()
                        / 3600,
                    },
                    "conversation_count": len(conversations),
                    "conversation_ids": sorted([conv.id for conv in conversations]),
                }

                results.append(result_data)
                timeframes.append(timeframe)

                print(f"     ✅ Found {len(conversations)} conversations")
                print(
                    f"     📊 IDs: {sorted([conv.id for conv in conversations])[:3]}{'...' if len(conversations) > 3 else ''}"
                )
                flush_logs()  # Show results immediately

            except Exception as e:
                print(f"     ❌ Error: {e}")
                flush_logs()
                import traceback

                traceback.print_exc()
                return False, []

        # Compare results for consistency
        consistency_passed = self._verify_consistency(results, period_name)
        return consistency_passed, results

    def _verify_consistency(self, results: List[Dict], period_name: str) -> bool:
        """Verify that all results in a group are consistent."""
        if len(results) < 2:
            print("     ⚠️  Not enough results to compare")
            return True

        base_result = results[0]
        inconsistencies = []

        print(f"\n  🔍 Verifying consistency for {period_name}:")

        # Check timeframe duration consistency
        base_duration = base_result["timeframe"]["duration_hours"]
        duration_tolerance = 1.0  # 1 hour tolerance for "today" vs "last 24 hours"

        for i, result in enumerate(results[1:], 1):
            # Check conversation count
            if result["conversation_count"] != base_result["conversation_count"]:
                inconsistencies.append(
                    f"Query {i+1} returned {result['conversation_count']} conversations, "
                    f"but query 1 returned {base_result['conversation_count']}"
                )

            # Check conversation IDs (should be identical set)
            if set(result["conversation_ids"]) != set(base_result["conversation_ids"]):
                different_convs = len(
                    set(result["conversation_ids"]).symmetric_difference(
                        set(base_result["conversation_ids"])
                    )
                )
                inconsistencies.append(
                    f"Query {i+1} returned different conversations ({different_convs} different IDs)"
                )

            # Check timeframe duration (with tolerance)
            duration_diff = abs(result["timeframe"]["duration_hours"] - base_duration)
            if duration_diff > duration_tolerance:
                inconsistencies.append(
                    f"Query {i+1} has timeframe duration {result['timeframe']['duration_hours']:.1f}h, "
                    f"but query 1 has {base_duration:.1f}h (diff: {duration_diff:.1f}h)"
                )

        # Report results
        if inconsistencies:
            print("     ❌ INCONSISTENCIES FOUND:")
            for issue in inconsistencies:
                print(f"       - {issue}")

            # Save detailed results for debugging
            debug_file = f".ask-intercom-dev/timeframe_debug_{period_name.replace('/', '_').replace(' ', '_')}.json"
            with open(debug_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"     📄 Debug details saved to: {debug_file}")

            return False
        else:
            print("     ✅ All queries returned identical results")
            print(
                f"     📊 Consistent: {base_result['conversation_count']} conversations"
            )
            return True

    async def run_comprehensive_test(self) -> bool:
        """Run the complete timeframe consistency test suite."""
        print("🧪 TIMEFRAME CONSISTENCY INTEGRATION TEST")
        print("=" * 60)
        print("Configuration:")
        print(f"  Model: {self.config.model}")
        print(f"  Max conversations: {self.config.max_conversations}")
        print(f"  Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(
            "  Note: Testing with higher limits to verify true containment relationships"
        )
        flush_logs()

        try:
            success = await self.test_equivalent_timeframes()

            print("\n" + "=" * 60)
            if success:
                print("🎉 ALL TIMEFRAME CONSISTENCY TESTS PASSED")
                print("✅ Different phrasings return identical conversation sets")
                print("✅ Containment relationships are correct")
                return True
            else:
                print("❌ TIMEFRAME CONSISTENCY TESTS FAILED")
                print("⚠️  Issues found in timeframe interpretation or containment")
                return False

        except Exception as e:
            print(f"\n❌ TEST SUITE FAILED WITH ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _test_containment_relationships(self, results_by_period: Dict) -> bool:
        """Test that larger timeframes contain smaller ones (1 week > 1 day > 1 hour)."""
        print("🔗 Verifying containment relationships...")

        # Extract representative results for each period
        period_data = {}
        for period_name, period_results in results_by_period.items():
            if period_results:
                # Use first result as representative
                period_data[period_name] = period_results[0]

        containment_tests = [
            ("24 hours / 1 day", "1 hour", "1 day should contain 1 hour conversations"),
            (
                "7 days / 1 week",
                "24 hours / 1 day",
                "1 week should contain 1 day conversations",
            ),
            ("7 days / 1 week", "1 hour", "1 week should contain 1 hour conversations"),
            (
                "30 days / 1 month",
                "7 days / 1 week",
                "1 month should contain 1 week conversations",
            ),
            (
                "30 days / 1 month",
                "24 hours / 1 day",
                "1 month should contain 1 day conversations",
            ),
            (
                "30 days / 1 month",
                "1 hour",
                "1 month should contain 1 hour conversations",
            ),
        ]

        all_passed = True

        for larger_period, smaller_period, description in containment_tests:
            if larger_period not in period_data or smaller_period not in period_data:
                print(f"     ⚠️  Skipping: {description} (missing data)")
                continue

            larger_data = period_data[larger_period]
            smaller_data = period_data[smaller_period]

            larger_ids = set(larger_data["conversation_ids"])
            smaller_ids = set(smaller_data["conversation_ids"])

            print(f"  🔍 Testing: {description}")
            print(f"     📊 {larger_period}: {len(larger_ids)} conversations")
            print(f"     📊 {smaller_period}: {len(smaller_ids)} conversations")

            # Check if larger timeframe contains all conversations from smaller timeframe
            missing_conversations = smaller_ids - larger_ids
            extra_conversations = larger_ids - smaller_ids

            # CRITICAL INSIGHT: This may be a data limitation, not a logic error
            if missing_conversations:
                print(
                    f"     ❌ CONTAINMENT VIOLATION: {len(missing_conversations)} conversations in {smaller_period} not found in {larger_period}"
                )
                print(
                    f"        Missing IDs: {sorted(missing_conversations)[:5]}{'...' if len(missing_conversations) > 5 else ''}"
                )
                print(
                    "        ⚠️  NOTE: This may indicate Intercom Search API pagination/filtering issues"
                )
                all_passed = False
            else:
                print(
                    f"     ✅ All {smaller_period} conversations found in {larger_period}"
                )

            if extra_conversations:
                print(
                    f"     📈 {larger_period} has {len(extra_conversations)} additional conversations"
                )

            # Additional debug: check if this violates logical expectations
            if len(smaller_ids) > len(larger_ids):
                print(
                    f"     🚨 LOGICAL VIOLATION: {smaller_period} ({len(smaller_ids)}) has MORE conversations than {larger_period} ({len(larger_ids)})"
                )
                print(
                    "        This suggests API pagination/limit issues, not timeframe logic errors"
                )

            # Check timeframe duration logic
            larger_duration = larger_data["timeframe"]["duration_hours"]
            smaller_duration = smaller_data["timeframe"]["duration_hours"]

            if larger_duration < smaller_duration:
                print(
                    f"     ❌ DURATION VIOLATION: {larger_period} ({larger_duration:.1f}h) shorter than {smaller_period} ({smaller_duration:.1f}h)"
                )
                all_passed = False
            else:
                print(
                    f"     ✅ Duration check passed: {larger_duration:.1f}h > {smaller_duration:.1f}h"
                )

            print()

        return all_passed


async def main():
    """Run the timeframe consistency test."""
    test = TimeframeConsistencyTest()
    success = await test.run_comprehensive_test()

    if not success:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
