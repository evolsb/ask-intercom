"""Intercom API client with MCP fallback."""

from datetime import datetime
from typing import List, Optional

import httpx

from .logger import get_logger
from .models import Conversation, ConversationFilters, Message

logger = get_logger("intercom_client")


class IntercomClient:
    """Intercom API client with MCP support and REST fallback."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.intercom.io"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._cached_app_id = None

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
        self, filters: ConversationFilters
    ) -> List[Conversation]:
        """Fetch conversations based on filters."""
        try:
            # TODO: Implement MCP client when available
            logger.info("MCP not implemented yet, using REST API")
            return await self._fetch_via_rest(filters)
        except Exception as e:
            logger.error(f"Failed to fetch conversations: {e}", exc_info=True)
            raise

    async def _fetch_via_rest(self, filters: ConversationFilters) -> List[Conversation]:
        """Fetch conversations via REST API."""
        try:
            # Try Search API first (much faster)
            return await self._fetch_via_search_api(filters)
        except Exception as e:
            logger.warning(
                f"Search API failed ({e}), falling back to list + details method"
            )
            return await self._fetch_via_list_and_details(filters)

    async def _fetch_via_search_api(
        self, filters: ConversationFilters
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

            # Build request body
            request_body = {
                "query": query,
                "pagination": {
                    "per_page": min(filters.limit, 150)  # Search API max is 150
                },
            }

            # Make search request
            response = await client.post(
                f"{self.base_url}/conversations/search",
                headers=self.headers,
                json=request_body,
            )
            response.raise_for_status()

            data = response.json()

            # Parse conversations directly from search results
            for conv_data in data.get("conversations", []):
                conversation = self._parse_conversation_from_search(conv_data)
                if conversation:
                    conversations.append(conversation)

        logger.info(f"Fetched {len(conversations)} conversations via Search API")
        return conversations

    async def _fetch_via_list_and_details(
        self, filters: ConversationFilters
    ) -> List[Conversation]:
        """Fetch conversations via old method (list + individual details)."""
        conversations = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Build query parameters
            params = {
                "per_page": min(filters.limit, 50),  # Intercom max is 50
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

                    if len(conversations) >= filters.limit:
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

                    message = Message(
                        id=str(part.get("id", "unknown")),
                        author_type=(
                            "admin"
                            if part.get("author", {}).get("type") == "admin"
                            else "user"
                        ),
                        body=part.get("body", ""),
                        created_at=datetime.fromtimestamp(part.get("created_at", 0)),
                    )
                    messages.append(message)

            # Add the initial message from source
            if conv_data.get("source", {}).get("body"):
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=conv_data["source"]["body"],
                    created_at=datetime.fromtimestamp(conv_data["created_at"]),
                )
                messages.insert(0, initial_message)

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
            for part in parts_data.get("conversation_parts", {}).get(
                "conversation_parts", []
            ):
                if part.get("part_type") in ["comment", "note"]:
                    message = Message(
                        id=part["id"],
                        author_type=(
                            "admin"
                            if part.get("author", {}).get("type") == "admin"
                            else "user"
                        ),
                        body=part.get("body", ""),
                        created_at=datetime.fromtimestamp(part["created_at"]),
                    )
                    messages.append(message)

            # Add the initial message
            if conv_data.get("source", {}).get("body"):
                initial_message = Message(
                    id=conv_data["id"] + "_initial",
                    author_type="user",
                    body=conv_data["source"]["body"],
                    created_at=datetime.fromtimestamp(conv_data["created_at"]),
                )
                messages.insert(0, initial_message)

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
