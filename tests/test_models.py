"""Unit tests for data models."""

from datetime import datetime

from src.models import (
    AnalysisResult,
    Conversation,
    ConversationFilters,
    CostInfo,
    Message,
    TimeFrame,
)


class TestTimeFrame:
    """Test TimeFrame data model."""

    def test_timeframe_creation(self):
        """Test basic TimeFrame creation."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        timeframe = TimeFrame(
            start_date=start, end_date=end, description="January 2024"
        )

        assert timeframe.start_date == start
        assert timeframe.end_date == end
        assert timeframe.description == "January 2024"

    def test_timeframe_string_representation(self):
        """Test TimeFrame has proper fields."""
        timeframe = TimeFrame(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            description="test period",
        )

        assert hasattr(timeframe, "start_date")
        assert hasattr(timeframe, "end_date")
        assert hasattr(timeframe, "description")


class TestMessage:
    """Test Message data model."""

    def test_message_creation(self):
        """Test basic Message creation."""
        created_at = datetime.now()
        message = Message(
            id="msg_123",
            author_type="user",
            body="Hello, I need help",
            created_at=created_at,
        )

        assert message.id == "msg_123"
        assert message.author_type == "user"
        assert message.body == "Hello, I need help"
        assert message.created_at == created_at

    def test_message_author_types(self):
        """Test different author types."""
        user_msg = Message(
            id="1",
            author_type="user",
            body="Customer message",
            created_at=datetime.now(),
        )
        admin_msg = Message(
            id="2",
            author_type="admin",
            body="Support response",
            created_at=datetime.now(),
        )

        assert user_msg.author_type == "user"
        assert admin_msg.author_type == "admin"


class TestConversation:
    """Test Conversation data model."""

    def test_conversation_creation_with_messages(self):
        """Test Conversation creation with messages."""
        messages = [
            Message(
                id="msg_1",
                author_type="user",
                body="I have a problem",
                created_at=datetime.now(),
            ),
            Message(
                id="msg_2",
                author_type="admin",
                body="How can I help?",
                created_at=datetime.now(),
            ),
        ]

        conversation = Conversation(
            id="conv_123",
            created_at=datetime.now(),
            messages=messages,
            customer_email="test@example.com",
        )

        assert conversation.id == "conv_123"
        assert len(conversation.messages) == 2
        assert conversation.customer_email == "test@example.com"
        assert conversation.tags == []  # Should default to empty list

    def test_conversation_tags_initialization(self):
        """Test that tags are properly initialized."""
        # Test with None tags (should become empty list)
        conv1 = Conversation(
            id="conv_1", created_at=datetime.now(), messages=[], tags=None
        )
        assert conv1.tags == []

        # Test with provided tags
        conv2 = Conversation(
            id="conv_2",
            created_at=datetime.now(),
            messages=[],
            tags=["bug", "urgent"],
        )
        assert conv2.tags == ["bug", "urgent"]

    def test_conversation_optional_fields(self):
        """Test conversation with optional fields as None."""
        conversation = Conversation(
            id="conv_minimal", created_at=datetime.now(), messages=[]
        )

        assert conversation.customer_email is None
        assert conversation.tags == []


class TestCostInfo:
    """Test CostInfo data model."""

    def test_cost_info_creation(self):
        """Test basic CostInfo creation."""
        cost_info = CostInfo(
            tokens_used=1500, estimated_cost_usd=0.045, model_used="gpt-4"
        )

        assert cost_info.tokens_used == 1500
        assert cost_info.estimated_cost_usd == 0.045
        assert cost_info.model_used == "gpt-4"

    def test_cost_info_different_models(self):
        """Test CostInfo with different models."""
        gpt4_cost = CostInfo(
            tokens_used=1000, estimated_cost_usd=0.06, model_used="gpt-4"
        )
        gpt35_cost = CostInfo(
            tokens_used=1000, estimated_cost_usd=0.002, model_used="gpt-3.5-turbo"
        )

        assert gpt4_cost.model_used == "gpt-4"
        assert gpt35_cost.model_used == "gpt-3.5-turbo"
        assert gpt4_cost.estimated_cost_usd > gpt35_cost.estimated_cost_usd


class TestAnalysisResult:
    """Test AnalysisResult data model."""

    def test_analysis_result_creation(self):
        """Test complete AnalysisResult creation."""
        timeframe = TimeFrame(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            description="January 2024",
        )
        cost_info = CostInfo(
            tokens_used=1200, estimated_cost_usd=0.036, model_used="gpt-4"
        )

        result = AnalysisResult(
            summary="Key findings from conversations",
            key_insights=["Login issues", "Billing confusion", "Feature requests"],
            conversation_count=25,
            time_range=timeframe,
            cost_info=cost_info,
        )

        assert result.summary == "Key findings from conversations"
        assert len(result.key_insights) == 3
        assert result.conversation_count == 25
        assert result.time_range == timeframe
        assert result.cost_info == cost_info


class TestConversationFilters:
    """Test ConversationFilters data model."""

    def test_filters_default_values(self):
        """Test default values for filters."""
        filters = ConversationFilters()

        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.tags is None
        assert filters.customer_email is None
        assert filters.limit == 50

    def test_filters_with_custom_values(self):
        """Test filters with custom values."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        filters = ConversationFilters(
            start_date=start_date,
            end_date=end_date,
            tags=["bug", "feature"],
            customer_email="test@example.com",
            limit=25,
        )

        assert filters.start_date == start_date
        assert filters.end_date == end_date
        assert filters.tags == ["bug", "feature"]
        assert filters.customer_email == "test@example.com"
        assert filters.limit == 25

    def test_filters_limit_variations(self):
        """Test different limit values."""
        filters_small = ConversationFilters(limit=10)
        filters_large = ConversationFilters(limit=100)

        assert filters_small.limit == 10
        assert filters_large.limit == 100
