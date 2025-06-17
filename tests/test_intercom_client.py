"""Integration tests for Intercom client with mocked API responses."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.intercom_client import IntercomClient
from src.models import ConversationFilters


class TestIntercomClientFetching:
    """Test conversation fetching functionality."""

    @pytest.fixture
    def intercom_client(self):
        """Create Intercom client for testing."""
        return IntercomClient(access_token="test_token_123456")

    @pytest.fixture
    def mock_conversations_response(self):
        """Mock Intercom API conversations response."""
        return {
            "conversations": [
                {
                    "id": "conv_123",
                    "created_at": 1705276800,  # 2024-01-15 00:00:00
                    "source": {
                        "body": "I need help with my account",
                        "delivered_as": {"contact": {"email": "user@example.com"}},
                    },
                    "tags": {"tags": ["support", "account"]},
                },
                {
                    "id": "conv_456",
                    "created_at": 1705363200,  # 2024-01-16 00:00:00
                    "source": {
                        "body": "Billing question",
                        "delivered_as": {"contact": {"email": "billing@example.com"}},
                    },
                    "tags": {"tags": ["billing"]},
                },
            ]
        }

    @pytest.fixture
    def mock_conversation_parts_response(self):
        """Mock Intercom API conversation parts response."""
        return {
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "id": "part_1",
                        "part_type": "comment",
                        "body": "Thanks for contacting us!",
                        "created_at": 1705277000,
                        "author": {"type": "admin"},
                    },
                    {
                        "id": "part_2",
                        "part_type": "comment",
                        "body": "Can you provide more details?",
                        "created_at": 1705277200,
                        "author": {"type": "admin"},
                    },
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_fetch_conversations_success(
        self,
        intercom_client,
        mock_conversations_response,
        mock_conversation_parts_response,
    ):
        """Test successful conversation fetching."""
        filters = ConversationFilters(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            limit=10,
        )

        # Mock httpx responses
        mock_list_response = AsyncMock()
        mock_list_response.raise_for_status.return_value = None
        mock_list_response.json.return_value = mock_conversations_response

        mock_parts_response = AsyncMock()
        mock_parts_response.raise_for_status.return_value = None
        mock_parts_response.json.return_value = mock_conversation_parts_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # First call for conversations list, subsequent calls for parts
            mock_client.get.side_effect = [
                mock_list_response,
                mock_parts_response,
                mock_parts_response,
            ]

            conversations = await intercom_client.fetch_conversations(filters)

            assert len(conversations) == 2
            assert conversations[0].id == "conv_123"
            assert conversations[0].customer_email == "user@example.com"
            assert "support" in conversations[0].tags
            assert len(conversations[0].messages) == 3  # Initial + 2 parts

            assert conversations[1].id == "conv_456"
            assert conversations[1].customer_email == "billing@example.com"

    @pytest.mark.asyncio
    async def test_fetch_conversations_with_date_filters(self, intercom_client):
        """Test conversation fetching with date filters."""
        filters = ConversationFilters(
            start_date=datetime(2024, 1, 15),
            end_date=datetime(2024, 1, 20),
            limit=5,
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"conversations": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            mock_client.get.return_value = mock_response

            await intercom_client.fetch_conversations(filters)

            # Verify the API call was made with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args

            assert "conversations" in call_args[0][0]
            assert call_args[1]["params"]["created_at_after"] == int(
                filters.start_date.timestamp()
            )
            assert call_args[1]["params"]["created_at_before"] == int(
                filters.end_date.timestamp()
            )
            assert call_args[1]["params"]["per_page"] == 5

    @pytest.mark.asyncio
    async def test_fetch_conversations_api_error(self, intercom_client):
        """Test handling of API errors."""
        filters = ConversationFilters(limit=10)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Simulate API error
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "API Error", request=None, response=None
            )

            with pytest.raises(httpx.HTTPStatusError):
                await intercom_client.fetch_conversations(filters)

    @pytest.mark.asyncio
    async def test_fetch_conversations_empty_response(self, intercom_client):
        """Test handling of empty API response."""
        filters = ConversationFilters(limit=10)

        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"conversations": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            mock_client.get.return_value = mock_response

            conversations = await intercom_client.fetch_conversations(filters)

            assert len(conversations) == 0

    @pytest.mark.asyncio
    async def test_fetch_conversations_limit_respected(
        self, intercom_client, mock_conversations_response
    ):
        """Test that conversation limit is respected."""
        filters = ConversationFilters(limit=1)

        mock_list_response = AsyncMock()
        mock_list_response.raise_for_status.return_value = None
        mock_list_response.json.return_value = mock_conversations_response

        mock_parts_response = AsyncMock()
        mock_parts_response.raise_for_status.return_value = None
        mock_parts_response.json.return_value = {
            "conversation_parts": {"conversation_parts": []}
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            mock_client.get.side_effect = [mock_list_response, mock_parts_response]

            conversations = await intercom_client.fetch_conversations(filters)

            # Should only return 1 conversation despite API returning 2
            assert len(conversations) == 1


class TestIntercomClientConversationParsing:
    """Test conversation parsing functionality."""

    @pytest.fixture
    def intercom_client(self):
        """Create Intercom client for testing."""
        return IntercomClient(access_token="test_token_123456")

    @pytest.mark.asyncio
    async def test_parse_conversation_with_parts(self, intercom_client):
        """Test parsing conversation with message parts."""
        conv_data = {
            "id": "conv_test",
            "created_at": 1705276800,
            "source": {
                "body": "Initial message",
                "delivered_as": {"contact": {"email": "test@example.com"}},
            },
            "tags": {"tags": ["test", "parsing"]},
        }

        parts_data = {
            "conversation_parts": {
                "conversation_parts": [
                    {
                        "id": "part_1",
                        "part_type": "comment",
                        "body": "Admin response",
                        "created_at": 1705277000,
                        "author": {"type": "admin"},
                    },
                    {
                        "id": "part_2",
                        "part_type": "note",
                        "body": "Internal note",
                        "created_at": 1705277200,
                        "author": {"type": "admin"},
                    },
                ]
            }
        }

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = parts_data

        conversation = await intercom_client._parse_conversation(mock_client, conv_data)

        assert conversation is not None
        assert conversation.id == "conv_test"
        assert conversation.customer_email == "test@example.com"
        assert len(conversation.messages) == 3  # Initial + 2 parts
        assert conversation.messages[0].body == "Initial message"
        assert conversation.messages[0].author_type == "user"
        assert conversation.messages[1].body == "Admin response"
        assert conversation.messages[1].author_type == "admin"
        assert "test" in conversation.tags

    @pytest.mark.asyncio
    async def test_parse_conversation_api_error(self, intercom_client):
        """Test parsing conversation when parts API fails."""
        conv_data = {
            "id": "conv_error",
            "created_at": 1705276800,
            "source": {"body": "Test message"},
        }

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Parts API Error", request=None, response=None
        )

        conversation = await intercom_client._parse_conversation(mock_client, conv_data)

        # Should return None when parsing fails
        assert conversation is None

    @pytest.mark.asyncio
    async def test_parse_conversation_minimal_data(self, intercom_client):
        """Test parsing conversation with minimal data."""
        conv_data = {
            "id": "conv_minimal",
            "created_at": 1705276800,
            "source": {"body": "Minimal message"},
        }

        parts_data = {"conversation_parts": {"conversation_parts": []}}

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = parts_data

        conversation = await intercom_client._parse_conversation(mock_client, conv_data)

        assert conversation is not None
        assert conversation.id == "conv_minimal"
        assert conversation.customer_email is None
        assert len(conversation.messages) == 1  # Just initial message
        assert conversation.tags == []


class TestIntercomClientConfiguration:
    """Test Intercom client configuration."""

    def test_client_initialization(self):
        """Test client initialization with token."""
        client = IntercomClient(access_token="test_token_123")

        assert client.access_token == "test_token_123"
        assert client.base_url == "https://api.intercom.io"
        assert client.headers["Authorization"] == "Bearer test_token_123"
        assert client.headers["Accept"] == "application/json"

    def test_client_headers(self):
        """Test proper header configuration."""
        client = IntercomClient(access_token="my_token")

        expected_headers = {
            "Authorization": "Bearer my_token",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        for key, value in expected_headers.items():
            assert client.headers[key] == value
