"""
MCP-based freshness checker - queries metadata via MCP protocol.

This replaces the filesystem-based freshness checker with proper MCP calls.
Works with MCP servers running anywhere - local, remote, containerized.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Tuple

from ..logger import get_logger

if TYPE_CHECKING:
    from ..models import ConversationFilters
    from .universal_adapter import UniversalMCPAdapter

logger = get_logger("mcp_freshness_checker")


class MCPFreshnessChecker:
    """Check data freshness via MCP protocol - works with remote servers."""

    def __init__(self, max_staleness_minutes: int = 60):
        self.max_staleness = timedelta(minutes=max_staleness_minutes)

    async def get_freshness_info(
        self, mcp_adapter: "UniversalMCPAdapter"
    ) -> Dict[str, any]:
        """
        Get freshness metadata via MCP protocol.

        This works regardless of where the MCP server is running.
        """
        try:
            # Check if the adapter has the new MCP tools implemented
            if (
                not hasattr(mcp_adapter, "backend")
                or not mcp_adapter.backend
                or not hasattr(mcp_adapter.backend, "call_tool")
            ):
                logger.warning("MCP adapter doesn't support call_tool method yet")
                return {
                    "status": "not_supported",
                    "has_data": False,
                    "error": "MCP tools not yet implemented",
                }

            # For HTTP MCP backend, always trust the external server
            if mcp_adapter.backend.backend_type == "http-mcp":
                logger.info("Using HTTP MCP backend - trusting external server data")
                return {
                    "status": "fresh",
                    "has_data": True,
                    "last_sync": datetime.now().isoformat(),
                    "note": "HTTP MCP server manages its own data freshness",
                }

            # Call MCP tool to get data info (if available)
            try:
                result = await mcp_adapter.backend.call_tool("get_data_info", {})
            except Exception as e:
                # If get_data_info is not available (e.g., LocalMCP), assume data is fresh
                logger.info(
                    f"get_data_info not available ({e}), assuming data is fresh for LocalMCP"
                )
                return {
                    "status": "fresh",
                    "has_data": True,
                    "last_sync": datetime.now().isoformat(),
                    "note": "LocalMCP uses real-time API calls",
                }

            # Handle mock/error responses during development
            if "error" in result:
                logger.warning(f"MCP data info not available: {result['error']}")
                return {
                    "status": "unknown",
                    "has_data": False,
                    "error": result["error"],
                }

            return {"status": "available", "has_data": True, **result}

        except Exception as e:
            logger.error(f"Failed to get MCP freshness info: {e}")
            return {"status": "error", "has_data": False, "error": str(e)}

    async def check_coverage(
        self,
        mcp_adapter: "UniversalMCPAdapter",
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, any]:
        """Check if MCP server has data covering the requested range."""
        try:
            # Check if the adapter has the new MCP tools implemented
            if (
                not hasattr(mcp_adapter, "backend")
                or not mcp_adapter.backend
                or not hasattr(mcp_adapter.backend, "call_tool")
            ):
                logger.warning("MCP adapter doesn't support call_tool method yet")
                return {"has_coverage": False, "error": "MCP tools not yet implemented"}

            # Call MCP tool to check coverage
            result = await mcp_adapter.backend.call_tool(
                "check_coverage",
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

            # Handle mock/error responses during development
            if "error" in result:
                logger.warning(f"MCP coverage check not available: {result['error']}")
                return {"has_coverage": False, "error": result["error"]}

            return result

        except Exception as e:
            logger.error(f"Failed to check MCP coverage: {e}")
            return {"has_coverage": False, "error": str(e)}

    async def should_use_mcp(
        self, mcp_adapter: "UniversalMCPAdapter", filters: "ConversationFilters"
    ) -> Tuple[bool, str, Dict]:
        """
        Determine if MCP should be used based on data freshness.

        Returns:
            (should_use, reason, metadata)
        """
        # Get data info from MCP server
        data_info = await self.get_freshness_info(mcp_adapter)

        # No data available
        if not data_info.get("has_data"):
            return False, "No data available in MCP server", data_info

        # Check staleness
        if "data_age_minutes" in data_info:
            age_minutes = data_info["data_age_minutes"]
            max_minutes = self.max_staleness.total_seconds() / 60

            if age_minutes > max_minutes:
                return (
                    False,
                    f"Data is {age_minutes} minutes old (max: {max_minutes})",
                    data_info,
                )

        # Check coverage
        coverage = await self.check_coverage(
            mcp_adapter, filters.start_date, filters.end_date
        )

        if not coverage.get("has_coverage"):
            return (
                False,
                "MCP data doesn't cover requested date range",
                {**data_info, **coverage},
            )

        return (
            True,
            "MCP data is fresh and covers query period",
            {**data_info, **coverage},
        )


async def should_use_mcp_for_query(
    mcp_adapter: "UniversalMCPAdapter",
    filters: "ConversationFilters",
    max_staleness_minutes: int = 60,
) -> Tuple[bool, str, Dict]:
    """
    High-level function to check if MCP should be used.

    This replaces the filesystem-based check with proper MCP protocol calls.
    """
    checker = MCPFreshnessChecker(max_staleness_minutes)
    return await checker.should_use_mcp(mcp_adapter, filters)
