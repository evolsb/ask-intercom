"""Intercom API client with MCP integration."""

import asyncio
import time
from datetime import datetime
from typing import List, Optional

import httpx

from .config import Config
from .logger import get_logger
from .models import Conversation, ConversationFilters, Message

logger = get_logger("intercom_client")


class IntercomClient:
    """Intercom API client with MCP integration."""

    def __init__(self, access_token: str, config: Optional[Config] = None):
        self.access_token = access_token
        self.config = config or Config.from_env()
        self.base_url = "https://api.intercom.io"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._cached_app_id = None

        # Initialize Universal MCP adapter if enabled
        self.mcp_adapter = None
        if self.config.enable_mcp:
            try:
                from .mcp.universal_adapter import create_universal_adapter

                # Create universal adapter with configured backend preference
                force_backend = self.config.mcp_backend

                self.universal_adapter = asyncio.create_task(
                    create_universal_adapter(
                        intercom_token=access_token,
                        prefer_fastintercom=(self.config.mcp_backend == "fastintercom"),
                        force_backend=force_backend,
                    )
                )
                logger.info("Universal MCP adapter initializing...")
            except Exception as e:
                logger.warning(f"Failed to initialize Universal MCP adapter: {e}")
                self.universal_adapter = None

    async def get_app_id(self) -> Optional[str]:
        """Fetch the workspace/app ID from Intercom API."""
        if self._cached_app_id:
            return self._cached_app_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try the /me endpoint first
                try:
                    response = await client.get(
                        f"{self.base_url}/me",
                        headers=self.headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # The app ID is in the nested "app" object with key "id_code"
                        if data.get("app") and data["app"].get("id_code"):
                            app_id = data["app"]["id_code"]
                            self._cached_app_id = str(app_id)
                            logger.info(f"Found app ID via /me endpoint: {app_id}")
                            return self._cached_app_id

                except Exception as e:
                    logger.debug(f"/me endpoint failed: {e}")

                # Try the admins endpoint (often includes workspace info)
                try:
                    response = await client.get(
                        f"{self.base_url}/admins",
                        headers=self.headers,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # Look for app_id in admin data
                        if data.get("admins") and len(data["admins"]) > 0:
                            admin = data["admins"][0]
                            app_id = admin.get("app_id") or admin.get("workspace_id")
                            if app_id:
                                self._cached_app_id = str(app_id)
                                logger.info(
                                    f"Found app ID via /admins endpoint: {app_id}"
                                )
                                return self._cached_app_id

                except Exception as e:
                    logger.debug(f"/admins endpoint failed: {e}")

                # As a fallback, try to extract from any conversation data we can get
                try:
                    # Get a small sample of conversations to see if we can extract app ID from URLs or data
                    response = await client.get(
                        f"{self.base_url}/conversations",
                        headers=self.headers,
                        params={"per_page": 1},
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # This is a stretch, but sometimes workspace info is embedded in responses
                        # We might find it in links or metadata
                        # For now, just log that we tried
                        logger.debug(
                            "Tried to extract app ID from conversations endpoint, no success"
                        )

                except Exception as e:
                    logger.debug(f"/conversations endpoint failed: {e}")

        except Exception as e:
            logger.warning(f"Failed to fetch app ID: {e}")

        logger.warning(
            "Could not determine app ID from Intercom API - conversation links will be disabled"
        )
        return None

    async def fetch_conversations(
        self, filters: ConversationFilters, progress_callback=None
    ) -> List[Conversation]:
        """Fetch conversations using MCP if available, otherwise REST API."""
        try:
            # Use MCP if available and enabled
            if self.config.enable_mcp and hasattr(self, "universal_adapter"):
                logger.info("Using MCP adapter for conversation fetching")
                try:
                    # Wait for adapter to be ready
                    adapter = await self.universal_adapter
                    conversations = await adapter.search_conversations(filters)

                    if progress_callback:
                        progress_callback(len(conversations), len(conversations))

                    logger.info(
                        f"MCP adapter fetched {len(conversations)} conversations"
                    )
                    return conversations

                except Exception as mcp_error:
                    # Check if it's a sync state exception that should be re-raised
                    from .mcp.fastintercom_backend import SyncStateException
                    if isinstance(mcp_error, SyncStateException):
                        logger.error(f"Data sync issue: {mcp_error}")
                        raise  # Re-raise to inform user about sync requirements
                    logger.warning(f"MCP failed, falling back to REST: {mcp_error}")
                    logger.info("Using REST API fallback for conversation fetching")
                    return await self._fetch_via_rest(filters, progress_callback)
            else:
                logger.info("Using REST API for conversation fetching")
                return await self._fetch_via_rest(filters, progress_callback)
        except Exception as e:
            logger.error(f"Failed to fetch conversations: {e}", exc_info=True)
            raise

    async def _fetch_via_rest(
        self, filters: ConversationFilters, progress_callback=None
    ) -> List[Conversation]:
        """Fetch conversations via REST API."""
        try:
            # Try Search API first (much faster)
            return await self._fetch_via_search_api(filters, progress_callback)
        except Exception as e:
            logger.warning(
                f"Search API failed ({e}), falling back to list + details method"
            )
            return await self._fetch_via_list_and_details(filters, progress_callback)

    async def _fetch_via_search_api(
        self, filters: ConversationFilters, progress_callback=None
    ) -> List[Conversation]:
        """Fetch conversations using the Search API (much faster)."""
        conversations = []

        # Optimize HTTP client for better performance
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
            # Build search query
            search_filters = []

            if filters.start_date:
                search_filters.append(
                    {
                        "field": "created_at",
                        "operator": ">",
                        "value": int(filters.start_date.timestamp()),
                    }
                )

            if filters.end_date:
                search_filters.append(
                    {
                        "field": "created_at",
                        "operator": "<",
                        "value": int(filters.end_date.timestamp()),
                    }
                )

            # Build query structure
            if len(search_filters) == 0:
                # No filters, get recent conversations
                query = {
                    "field": "created_at",
                    "operator": ">",
                    "value": 0,  # All conversations
                }
            elif len(search_filters) == 1:
                query = search_filters[0]
            else:
                query = {"operator": "AND", "value": search_filters}

            # Pagination loop to get ALL conversations within the timeframe
            page = 1
            per_page = 150  # Search API max is 150 - use full page size for efficiency
            max_conversations = (
                min(filters.limit, 1000) if filters.limit is not None else 1000
            )  # Use requested limit, capped at 1000 for safety
            estimated_total = None  # Will be set after first API call
            fetch_start_time = None  # Track fetching start time for rate calculation

            while len(conversations) < max_conversations:
                # Build request body with pagination and sorting
                request_body = {
                    "query": query,
                    "pagination": {"per_page": per_page, "page": page},
                    "sort": {
                        "field": "created_at",
                        "order": "desc",  # Consistent ordering
                    },
                }

                logger.debug(f"Fetching Search API page {page} (per_page={per_page})")

                # Make search request
                response = await client.post(
                    f"{self.base_url}/conversations/search",
                    headers=self.headers,
                    json=request_body,
                )
                response.raise_for_status()

                data = response.json()
                page_conversations = data.get("conversations", [])

                # Set estimated total from first response
                if estimated_total is None:
                    estimated_total = data.get("total_count", 0)
                    fetch_start_time = time.time()  # Start timing from first response
                    if progress_callback and estimated_total > 0:
                        await progress_callback(
                            "fetching",
                            f"Found {estimated_total} conversations to fetch...",
                            25,
                        )

                # No more results
                if not page_conversations:
                    logger.debug(
                        f"No more conversations on page {page}, stopping pagination"
                    )
                    break

                # Parse conversations from this page
                page_count = 0
                for conv_data in page_conversations:
                    if len(conversations) >= max_conversations:
                        break
                    conversation = self._parse_conversation_from_search(conv_data)
                    if conversation:
                        conversations.append(conversation)
                        page_count += 1

                logger.info(
                    f"Page {page}: Parsed {page_count} conversations (total: {len(conversations)})"
                )

                # Report progress if callback provided
                if (
                    progress_callback
                    and estimated_total
                    and estimated_total > 0
                    and fetch_start_time
                ):
                    # Calculate progress: 25% (initial) + 25% (fetching progress)
                    fetch_progress = min(len(conversations) / estimated_total, 1.0)
                    total_percent = 25 + int(fetch_progress * 25)  # 25% to 50%

                    # Calculate progress percentage and ETA
                    elapsed_time = time.time() - fetch_start_time
                    progress_pct = (
                        (len(conversations) / estimated_total * 100)
                        if estimated_total > 0
                        else 0
                    )

                    if elapsed_time > 1.0:  # Only show rate/ETA after reasonable time
                        rate = len(conversations) / elapsed_time
                        remaining = estimated_total - len(conversations)
                        eta = int(remaining / rate) if rate > 0 and remaining > 0 else 0

                        # Cap rate display at reasonable values
                        if rate > 1000:
                            progress_msg = f"Fetched {len(conversations)}/{estimated_total} conversations ({progress_pct:.0f}% complete)"
                        elif eta > 0:
                            progress_msg = f"Fetched {len(conversations)}/{estimated_total} conversations ({rate:.0f}/sec, ETA: {eta}s)"
                        else:
                            progress_msg = f"Fetched {len(conversations)}/{estimated_total} conversations ({rate:.0f}/sec)"
                    else:
                        progress_msg = f"Fetched {len(conversations)}/{estimated_total} conversations ({progress_pct:.0f}% complete)"

                    await progress_callback("fetching", progress_msg, total_percent)

                # Check if this was the last page
                total_count = data.get("total_count", len(page_conversations))
                if (
                    len(page_conversations) < per_page
                    or (page * per_page) >= total_count
                ):
                    logger.info(
                        f"Reached end of results (page_size={len(page_conversations)}, total={total_count})"
                    )
                    break

                page += 1

                # Rate limiting - Intercom allows 83 requests per 10 seconds
                # Add small delay to be safe (aim for ~60 requests/10s)
                if page > 1:
                    await asyncio.sleep(
                        0.2
                    )  # 200ms between requests = ~5 requests/second

        # Log total found
        total_found = len(conversations)
        logger.info(
            f"Found {total_found} total conversations in the specified timeframe"
        )

        # Only trim if we exceed requested limit (shouldn't happen with new logic)
        if filters.limit is not None and len(conversations) > filters.limit:
            logger.warning(
                f"Found {len(conversations)} conversations, exceeding requested limit of {filters.limit}. Trimming to limit."
            )
            conversations = conversations[: filters.limit]
            logger.info(
                f"Fetched {len(conversations)} conversations (trimmed from {total_found})"
            )
        else:
            if filters.limit is not None:
                logger.info(
                    f"Fetched {len(conversations)} conversations (within requested limit of {filters.limit})"
                )
            else:
                logger.info(
                    f"Fetched {len(conversations)} conversations (no limit set)"
                )

        return conversations

    async def _fetch_via_list_and_details(
        self, filters: ConversationFilters, progress_callback=None
    ) -> List[Conversation]:
        """Fetch conversations via old method (list + individual details)."""
        conversations = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query parameters
            params = {
                "per_page": min(filters.limit or 50, 50),  # Intercom max is 50
                "order": "desc",
                "sort": "created_at",
            }

            if filters.start_date:
                params["created_at_after"] = int(filters.start_date.timestamp())
            if filters.end_date:
                params["created_at_before"] = int(filters.end_date.timestamp())

            response = await client.get(
                f"{self.base_url}/conversations",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()

            data = response.json()

            for conv_data in data.get("conversations", []):
                conversation = await self._parse_conversation_with_details(
                    client, conv_data
                )
                if conversation:
                    conversations.append(conversation)

                    if (
                        filters.limit is not None
                        and len(conversations) >= filters.limit
                    ):
                        break

        logger.info(f"Fetched {len(conversations)} conversations via list + details")
        return conversations

    def _parse_conversation_from_search(
        self, conv_data: dict
    ) -> Optional[Conversation]:
        """Parse a conversation from Search API response (includes conversation_parts)."""
        try:
            logger.debug(f"Parsing search conversation: {conv_data.get('id')}")

            # Parse messages from conversation_parts (already included in search response)
            messages = []
            has_customer_message = False

            conversation_parts = conv_data.get("conversation_parts", {})
            if isinstance(conversation_parts, dict):
                parts_list = conversation_parts.get("conversation_parts", [])
            else:
                parts_list = []

            for part in parts_list:
                # Skip if not a dict
                if not isinstance(part, dict):
                    continue

                if part.get("part_type") in ["comment", "note", "message"]:
                    # Skip parts without body
                    if not part.get("body"):
                        continue

                    author_type = (
                        "admin"
                        if part.get("author", {}).get("type") == "admin"
                        else "user"
                    )

                    body = part.get("body", "")

                    if author_type == "user":
                        has_customer_message = True

                    message = Message(
                        id=str(part.get("id", "unknown")),
                        author_type=author_type,
                        body=body,
                        created_at=datetime.fromtimestamp(part.get("created_at", 0)),
                    )
                    messages.append(message)

            # Add the initial message from source
            if conv_data.get("source", {}).get("body"):
                body = conv_data["source"]["body"]
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=body,
                    created_at=datetime.fromtimestamp(conv_data["created_at"]),
                )
                messages.insert(0, initial_message)
                has_customer_message = True

            # Skip conversations with only admin messages
            if not has_customer_message:
                logger.debug(f"Skipping admin-only conversation {conv_data.get('id')}")
                return None

            # Get customer email from source.author
            customer_email = None
            source = conv_data.get("source", {})
            if isinstance(source, dict):
                author = source.get("author", {})
                if isinstance(author, dict):
                    customer_email = author.get("email")

            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"]),
                messages=messages,
                customer_email=customer_email,
                tags=[
                    tag.get("name", tag) if isinstance(tag, dict) else tag
                    for tag in conv_data.get("tags", {}).get("tags", [])
                ],
            )

        except Exception as e:
            logger.warning(
                f"Failed to parse search conversation {conv_data.get('id') if isinstance(conv_data, dict) else 'unknown'}: {e}"
            )
            return None

    async def _parse_conversation_with_details(
        self, client: httpx.AsyncClient, conv_data: dict
    ) -> Optional[Conversation]:
        """Parse a conversation from list API response (requires separate details call)."""
        try:
            logger.debug(f"Parsing conversation with details: {conv_data.get('id')}")
            logger.debug(
                f"Conv data keys: {list(conv_data.keys()) if isinstance(conv_data, dict) else type(conv_data)}"
            )
            # Get conversation parts (messages)
            parts_response = await client.get(
                f"{self.base_url}/conversations/{conv_data['id']}",
                headers=self.headers,
            )
            parts_response.raise_for_status()
            parts_data = parts_response.json()

            # Parse messages
            messages = []
            has_customer_message = False

            for part in parts_data.get("conversation_parts", {}).get(
                "conversation_parts", []
            ):
                if part.get("part_type") in ["comment", "note"]:
                    author_type = (
                        "admin"
                        if part.get("author", {}).get("type") == "admin"
                        else "user"
                    )

                    body = part.get("body", "")

                    if author_type == "user":
                        has_customer_message = True

                    message = Message(
                        id=part["id"],
                        author_type=author_type,
                        body=body,
                        created_at=datetime.fromtimestamp(part["created_at"]),
                    )
                    messages.append(message)

            # Add the initial message
            if conv_data.get("source", {}).get("body"):
                body = conv_data["source"]["body"]
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=body,
                    created_at=datetime.fromtimestamp(conv_data["created_at"]),
                )
                messages.insert(0, initial_message)
                has_customer_message = True

            # Skip conversations with only admin messages
            if not has_customer_message:
                logger.debug(f"Skipping admin-only conversation {conv_data.get('id')}")
                return None

            # Get customer email from source.author or contacts
            customer_email = None
            source = conv_data.get("source", {})
            if isinstance(source, dict):
                author = source.get("author", {})
                if isinstance(author, dict):
                    customer_email = author.get("email")

            return Conversation(
                id=conv_data["id"],
                created_at=datetime.fromtimestamp(conv_data["created_at"]),
                messages=messages,
                customer_email=customer_email,
                tags=[
                    tag.get("name", tag) if isinstance(tag, dict) else tag
                    for tag in conv_data.get("tags", {}).get("tags", [])
                ],
            )

        except Exception as e:
            logger.warning(
                f"Failed to parse conversation {conv_data.get('id') if isinstance(conv_data, dict) else 'unknown'}: {e}"
            )
            logger.debug(f"Conv data type: {type(conv_data)}")
            logger.debug(f"Error type: {type(e).__name__}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
