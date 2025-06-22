"""
FastIntercom MCP Backend - High-performance caching backend.

This backend integrates FastIntercomMCP's caching and intelligent sync
capabilities into our universal adapter architecture.
"""

import asyncio
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logger import get_logger

logger = get_logger("fastintercom_backend")


class FastIntercomDatabase:
    """Lightweight wrapper around FastIntercomMCP's database functionality."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Path.home() / ".fastintercom" / "data.db"
        self._ensure_fastintercom_available()

    def _ensure_fastintercom_available(self):
        """Ensure FastIntercomMCP is available in the system."""
        try:
            # Check if fastintercom is available as an installed package
            import importlib.util

            spec = importlib.util.find_spec("fastintercom")
            if spec is not None:
                logger.info("FastIntercomMCP package found")
                return True
            else:
                logger.warning("FastIntercomMCP package not found")
                return False
        except ImportError:
            logger.warning(
                "FastIntercomMCP package not installed. Install with: pip install fastintercom"
            )
            return False
        except Exception as e:
            logger.warning(f"Failed to check FastIntercomMCP availability: {e}")
            return False

    async def search_conversations(
        self,
        query: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        customer_email: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search conversations using FastIntercomMCP's database."""
        try:
            # Import FastIntercomMCP modules (requires package installation)
            from fastintercom.database import DatabaseManager
            from fastintercom.models import ConversationFilters

            db = DatabaseManager(str(self.db_path))

            # Convert to FastIntercomMCP format
            filters = ConversationFilters(
                query=query,
                start_date=start_date,
                end_date=end_date,
                customer_email=customer_email,
                limit=limit,
            )

            conversations = db.search_conversations(
                query=filters.query,
                start_date=filters.start_date,
                end_date=filters.end_date,
                customer_email=filters.customer_email,
                limit=filters.limit,
            )

            # Convert back to our format
            result = []
            for conv in conversations:
                result.append(
                    {
                        "id": conv.id,
                        "created_at": conv.created_at.isoformat(),
                        "updated_at": conv.updated_at.isoformat(),
                        "customer_email": conv.customer_email,
                        "tags": conv.tags,
                        "messages": [
                            {
                                "id": msg.id,
                                "author_type": msg.author_type,
                                "body": msg.body,
                                "created_at": msg.created_at.isoformat(),
                                "part_type": msg.part_type,
                            }
                            for msg in conv.messages
                        ],
                    }
                )

            return result

        except Exception as e:
            logger.error(f"FastIntercomMCP search failed: {e}")
            return []

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific conversation by ID."""
        conversations = await self.search_conversations(limit=1000)  # Get all to search
        for conv in conversations:
            if conv["id"] == conversation_id:
                return conv
        return None

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get database sync status."""
        try:
            from fastintercom.database import DatabaseManager

            db = DatabaseManager(str(self.db_path))
            status = db.get_sync_status()
            return status
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {
                "database_size_mb": 0,
                "total_conversations": 0,
                "total_messages": 0,
                "last_sync": None,
                "database_path": str(self.db_path),
            }

    async def trigger_sync(self, force: bool = False) -> Dict[str, Any]:
        """Trigger FastIntercomMCP sync."""
        try:
            cmd = ["python", "-m", "fastintercom.cli", "sync"]
            if force:
                cmd.extend(["--force", "--days", "7"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            if result.returncode == 0:
                return {"success": True, "output": result.stdout, "error": None}
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Sync operation timed out"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}


class FastIntercomBackend:
    """Backend using FastIntercomMCP's caching and intelligent sync."""

    def __init__(self, intercom_token: str):
        self.intercom_token = intercom_token
        self.db = FastIntercomDatabase()
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize FastIntercomMCP backend."""
        try:
            logger.info("Initializing FastIntercomMCP backend")

            # Check if database exists and has data
            if not self.db.db_path.exists():
                logger.info("FastIntercomMCP database not found, initializing...")

                # Try to initialize FastIntercomMCP
                try:
                    # Set environment variable for token
                    env = os.environ.copy()
                    env["INTERCOM_ACCESS_TOKEN"] = self.intercom_token

                    # Initialize FastIntercomMCP
                    result = subprocess.run(
                        ["python", "-m", "fastintercom.cli", "init"],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=30,
                    )

                    if result.returncode != 0:
                        logger.warning(f"FastIntercomMCP init failed: {result.stderr}")
                        return False

                    # Do initial sync
                    sync_result = await self.db.trigger_sync(force=True)
                    if not sync_result["success"]:
                        logger.warning(f"Initial sync failed: {sync_result['error']}")
                        return False

                except Exception as e:
                    logger.warning(f"Failed to initialize FastIntercomMCP: {e}")
                    return False

            # Test database access
            status = await self.db.get_sync_status()
            if status["total_conversations"] == 0:
                logger.info("No conversations in FastIntercomMCP database yet")
                # Trigger a sync to get some data
                sync_result = await self.db.trigger_sync(force=True)
                if not sync_result["success"]:
                    logger.warning("No data available and sync failed")
                    return False

            self.initialized = True
            logger.info(
                f"FastIntercomMCP backend initialized with {status['total_conversations']} conversations"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize FastIntercomMCP backend: {e}")
            return False

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via FastIntercomMCP backend."""
        if not self.initialized:
            raise Exception("FastIntercomMCP backend not initialized")

        if tool_name == "search_conversations":
            return await self._search_conversations(params)
        elif tool_name == "get_conversation":
            return await self._get_conversation(params)
        elif tool_name == "get_server_status":
            return await self._get_server_status(params)
        elif tool_name == "sync_conversations":
            return await self._sync_conversations(params)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _search_conversations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search conversations using FastIntercomMCP cache."""
        query = params.get("query")
        limit = params.get("limit", 50)

        # Parse date filters
        start_date = None
        end_date = None

        if params.get("created_after"):
            start_date = datetime.fromisoformat(
                params["created_after"].replace("Z", "+00:00")
            )
        if params.get("created_before"):
            end_date = datetime.fromisoformat(
                params["created_before"].replace("Z", "+00:00")
            )

        # Check data freshness and trigger background sync if needed
        if start_date and end_date:
            # Check if we need to sync this timeframe
            now = datetime.now()
            if (now - end_date).total_seconds() < 3600:  # Last hour
                # Trigger background sync for recent data
                asyncio.create_task(self._background_sync())

        conversations = await self.db.search_conversations(
            query=query,
            start_date=start_date,
            end_date=end_date,
            customer_email=params.get("customer_email"),
            limit=limit,
        )

        return {"conversations": conversations}

    async def _get_conversation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get specific conversation."""
        conversation_id = params.get("conversation_id")
        if not conversation_id:
            raise ValueError("conversation_id is required")

        conversation = await self.db.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        return conversation

    async def _get_server_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get FastIntercomMCP server status."""
        status = await self.db.get_sync_status()
        return {
            "backend_type": "fastintercom",
            "status": "active",
            "database_size_mb": status["database_size_mb"],
            "total_conversations": status["total_conversations"],
            "total_messages": status["total_messages"],
            "last_sync": status["last_sync"],
            "database_path": status["database_path"],
        }

    async def _sync_conversations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger manual sync."""
        force = params.get("force", False)
        sync_result = await self.db.trigger_sync(force=force)

        if sync_result["success"]:
            return {
                "success": True,
                "message": "Sync completed successfully",
                "output": sync_result["output"],
            }
        else:
            return {
                "success": False,
                "message": "Sync failed",
                "error": sync_result["error"],
            }

    async def _background_sync(self):
        """Trigger background sync for recent data."""
        try:
            logger.info("Triggering background sync for recent data")
            await self.db.trigger_sync(force=False)
        except Exception as e:
            logger.warning(f"Background sync failed: {e}")

    async def close(self):
        """Clean up resources."""
        # FastIntercomMCP manages its own resources
        pass

    @property
    def backend_type(self) -> str:
        return "fastintercom"
