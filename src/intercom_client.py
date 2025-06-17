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
                conversation = await self._parse_conversation(client, conv_data)
                if conversation:
                    conversations.append(conversation)

                    if len(conversations) >= filters.limit:
                        break

        logger.info(f"Fetched {len(conversations)} conversations")
        return conversations

    async def _parse_conversation(
        self, client: httpx.AsyncClient, conv_data: dict
    ) -> Optional[Conversation]:
        """Parse a conversation from API response."""
        try:
            logger.debug(f"Parsing conversation: {conv_data.get('id')}")
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
