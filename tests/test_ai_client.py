"""Integration tests for AI client with mocked OpenAI responses."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.ai_client import AIClient
from src.models import Conversation, Message


class TestAIClientTimeframeInterpretation:
    """Test timeframe interpretation functionality."""

    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            api_key="sk-test_key_123456", model="gpt-4"  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_interpret_timeframe_this_month(self, ai_client):
        """Test timeframe interpretation for 'this month'."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"start_date": "2024-01-01", "end_date": "2024-01-31", "description": "this month"}'
                    }
                }
            ]
        }

        with patch.object(
            ai_client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create proper mock response structure
            mock_message = type(
                "Message",
                (),
                {"content": mock_response["choices"][0]["message"]["content"]},
            )()
            mock_choice = type("Choice", (), {"message": mock_message})()
            mock_create.return_value = type(
                "Response", (), {"choices": [mock_choice]}
            )()

            result = await ai_client._interpret_timeframe("What happened this month?")

            assert result.description == "this month"
            assert result.start_date.year == 2024
            assert result.start_date.month == 1
            assert result.end_date.month == 1

    @pytest.mark.asyncio
    async def test_interpret_timeframe_fallback(self, ai_client):
        """Test timeframe fallback when parsing fails."""
        mock_response = {"choices": [{"message": {"content": "invalid json response"}}]}

        with patch.object(
            ai_client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_message = type(
                "Message",
                (),
                {"content": mock_response["choices"][0]["message"]["content"]},
            )()
            mock_choice = type("Choice", (), {"message": mock_message})()
            mock_create.return_value = type(
                "Response", (), {"choices": [mock_choice]}
            )()

            result = await ai_client._interpret_timeframe("What happened recently?")

            # Should fallback to last 30 days
            assert result.description == "last 30 days"
            assert isinstance(result.start_date, datetime)
            assert isinstance(result.end_date, datetime)

    @pytest.mark.asyncio
    async def test_interpret_timeframe_last_week(self, ai_client):
        """Test timeframe interpretation for 'last week'."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"start_date": "2024-01-15", "end_date": "2024-01-21", "description": "last week"}'
                    }
                }
            ]
        }

        with patch.object(
            ai_client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_message = type(
                "Message",
                (),
                {"content": mock_response["choices"][0]["message"]["content"]},
            )()
            mock_choice = type("Choice", (), {"message": mock_message})()
            mock_create.return_value = type(
                "Response", (), {"choices": [mock_choice]}
            )()

            result = await ai_client._interpret_timeframe("Issues from last week")

            assert result.description == "last week"
            assert result.start_date.day == 15
            assert result.end_date.day == 21


class TestAIClientConversationAnalysis:
    """Test conversation analysis functionality."""

    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            api_key="sk-test_key_123456", model="gpt-4"  # pragma: allowlist secret
        )

    @pytest.fixture
    def sample_conversations(self):
        """Create sample conversations for testing."""
        return [
            Conversation(
                id="conv_1",
                created_at=datetime(2024, 1, 15),
                messages=[
                    Message(
                        id="msg_1",
                        author_type="user",
                        body="I can't log into my account",
                        created_at=datetime(2024, 1, 15),
                    ),
                    Message(
                        id="msg_2",
                        author_type="admin",
                        body="Let me help you with that login issue",
                        created_at=datetime(2024, 1, 15),
                    ),
                ],
                customer_email="user1@example.com",
                tags=["login", "support"],
            ),
            Conversation(
                id="conv_2",
                created_at=datetime(2024, 1, 16),
                messages=[
                    Message(
                        id="msg_3",
                        author_type="user",
                        body="The billing page is confusing",
                        created_at=datetime(2024, 1, 16),
                    ),
                ],
                customer_email="user2@example.com",
                tags=["billing"],
            ),
        ]

    @pytest.mark.asyncio
    async def test_analyze_conversations_success(self, ai_client, sample_conversations):
        """Test successful conversation analysis."""
        # Mock timeframe interpretation
        mock_timeframe_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"start_date": "2024-01-01", "end_date": "2024-01-31", "description": "this month"}'
                    }
                }
            ]
        }

        # Mock analysis response
        mock_analysis_response = {
            "choices": [
                {
                    "message": {
                        "content": """Based on the conversations, here are the key insights:

• Login issues are the primary concern, affecting 50% of users
• Billing page confusion is causing customer frustration
• Support team is responsive and helpful"""
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 150,
                "total_tokens": 1150,
            },
        }

        with patch.object(
            ai_client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create proper mock responses
            def create_mock_response(response_data):
                mock_message = type(
                    "Message",
                    (),
                    {"content": response_data["choices"][0]["message"]["content"]},
                )()
                mock_choice = type("Choice", (), {"message": mock_message})()
                mock_response = type("Response", (), {"choices": [mock_choice]})()
                if "usage" in response_data:
                    mock_response.usage = type("Usage", (), response_data["usage"])()
                return mock_response

            # First call for timeframe, second for analysis
            mock_create.side_effect = [
                create_mock_response(mock_timeframe_response),
                create_mock_response(mock_analysis_response),
            ]

            result = await ai_client.analyze_conversations(
                sample_conversations, "What are the main issues?"
            )

            assert result.conversation_count == 2
            assert "Login issues" in result.summary
            assert len(result.key_insights) >= 2
            assert result.cost_info.tokens_used == 1150
            assert result.cost_info.model_used == "gpt-4"
            assert result.cost_info.estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_analyze_conversations_empty_list(self, ai_client):
        """Test analysis with empty conversation list."""
        mock_timeframe_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"start_date": "2024-01-01", "end_date": "2024-01-31", "description": "this month"}'
                    }
                }
            ]
        }

        mock_analysis_response = {
            "choices": [{"message": {"content": "No conversations to analyze."}}],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 10,
                "total_tokens": 60,
            },
        }

        with patch.object(
            ai_client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            # Create proper mock responses
            def create_mock_response(response_data):
                mock_message = type(
                    "Message",
                    (),
                    {"content": response_data["choices"][0]["message"]["content"]},
                )()
                mock_choice = type("Choice", (), {"message": mock_message})()
                mock_response = type("Response", (), {"choices": [mock_choice]})()
                if "usage" in response_data:
                    mock_response.usage = type("Usage", (), response_data["usage"])()
                return mock_response

            mock_create.side_effect = [
                create_mock_response(mock_timeframe_response),
                create_mock_response(mock_analysis_response),
            ]

            result = await ai_client.analyze_conversations([], "What happened?")

            assert result.conversation_count == 0
            assert result.cost_info.tokens_used == 60


class TestAIClientCostCalculation:
    """Test cost calculation functionality."""

    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            api_key="sk-test_key_123456", model="gpt-4"  # pragma: allowlist secret
        )

    def test_calculate_cost_gpt4(self, ai_client):
        """Test cost calculation for GPT-4."""
        mock_usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "total_tokens": 1200,
            },
        )()

        cost_info = ai_client._calculate_cost(mock_usage)

        assert cost_info.tokens_used == 1200
        assert cost_info.model_used == "gpt-4"
        # GPT-4: $0.03 input + $0.06 output per 1K tokens
        # 1000 * 0.03/1000 + 200 * 0.06/1000 = 0.03 + 0.012 = 0.042
        assert abs(cost_info.estimated_cost_usd - 0.042) < 0.001

    def test_calculate_cost_gpt35(self):
        """Test cost calculation for GPT-3.5."""
        ai_client = AIClient(
            api_key="sk-test_key", model="gpt-3.5-turbo"  # pragma: allowlist secret
        )

        mock_usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "total_tokens": 1200,
            },
        )()

        cost_info = ai_client._calculate_cost(mock_usage)

        assert cost_info.model_used == "gpt-3.5-turbo"
        # GPT-3.5: $0.0005 input + $0.0015 output per 1K tokens
        # 1000 * 0.0005/1000 + 200 * 0.0015/1000 = 0.0005 + 0.0003 = 0.0008
        assert abs(cost_info.estimated_cost_usd - 0.0008) < 0.0001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model (defaults to GPT-4)."""
        ai_client = AIClient(
            api_key="sk-test_key", model="unknown-model"  # pragma: allowlist secret
        )

        mock_usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 500,
                "completion_tokens": 100,
                "total_tokens": 600,
            },
        )()

        cost_info = ai_client._calculate_cost(mock_usage)

        assert cost_info.model_used == "unknown-model"
        # Should use GPT-4 pricing as fallback
        expected_cost = (500 * 0.03 / 1000) + (100 * 0.06 / 1000)
        assert abs(cost_info.estimated_cost_usd - expected_cost) < 0.001


class TestAIClientJSONCleanup:
    """Test JSON cleanup functionality."""

    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            api_key="sk-test_key_123456", model="gpt-4"  # pragma: allowlist secret
        )

    def test_cleanup_json_valid_json(self, ai_client):
        """Test cleanup with already valid JSON."""
        valid_json = '{"key": "value", "number": 123}'
        result = ai_client._cleanup_json_response(valid_json)
        assert result == valid_json

    def test_cleanup_json_with_code_blocks(self, ai_client):
        """Test cleanup removes code block markers."""
        json_with_blocks = '```json\n{"key": "value"}\n```'
        result = ai_client._cleanup_json_response(json_with_blocks)
        assert result == '{"key": "value"}'

        json_with_generic_blocks = '```\n{"key": "value"}\n```'
        result = ai_client._cleanup_json_response(json_with_generic_blocks)
        assert result == '{"key": "value"}'

    def test_cleanup_json_whitespace(self, ai_client):
        """Test cleanup removes leading/trailing whitespace."""
        json_with_whitespace = '   \n  {"key": "value"}  \n  '
        result = ai_client._cleanup_json_response(json_with_whitespace)
        assert result == '{"key": "value"}'

    def test_cleanup_json_empty_string(self, ai_client):
        """Test cleanup handles empty string."""
        result = ai_client._cleanup_json_response("")
        assert result == ""

    def test_cleanup_json_none_input(self, ai_client):
        """Test cleanup handles None input."""
        result = ai_client._cleanup_json_response(None)
        assert result is None

    def test_cleanup_json_unterminated_string_recovery(self, ai_client):
        """Test recovery from unterminated string errors."""
        # Simulate JSON that's cut off mid-string
        incomplete_json = """{
    "insights": [
        {
            "title": "Login Issues",
            "description": "Users are having trouble with login
        }
    ]
}"""

        # This should attempt recovery by truncating and closing braces
        result = ai_client._cleanup_json_response(incomplete_json)

        # Should return valid JSON (either original or recovered version)
        import json

        try:
            parsed = json.loads(result)
            # If recovery worked, should have some structure
            assert isinstance(parsed, dict)
        except json.JSONDecodeError:
            # If recovery failed, should return original
            assert result == incomplete_json

    def test_cleanup_json_malformed_recovery_attempt(self, ai_client):
        """Test recovery attempts with various malformed JSON patterns."""
        test_cases = [
            # Missing closing brace
            '{"key": "value"',
            # Missing closing bracket
            '{"array": ["item1", "item2"',
            # Multiple levels missing braces
            '{"level1": {"level2": {"key": "value"',
        ]

        for malformed_json in test_cases:
            result = ai_client._cleanup_json_response(malformed_json)

            # Should either fix it (make it valid JSON) or return original
            import json

            try:
                json.loads(result)
                # If parsed successfully, recovery worked
                assert True
            except json.JSONDecodeError:
                # If still invalid, should return original unchanged
                assert result == malformed_json

    def test_cleanup_json_complex_unterminated_scenario(self, ai_client):
        """Test complex unterminated string recovery scenario."""
        # Simulate a more complex case with actual AI response structure
        complex_incomplete = """{
    "insights": [
        {
            "id": "login_issues",
            "category": "BUG",
            "title": "Login Problems",
            "description": "Users experiencing login difficulties",
            "customers": [
                {
                    "email": "user1@example.com",
                    "conversation_url": "https://app.intercom.com/conv/123"
                }
            ],
            "impact": {
                "customer_count": 5,
                "percentage": 25.0
            },
            "priority_score": 8,
            "recommendation": "Fix authentication service
        }
    ],
    "summary": {
        "total_conversations": 20"""

        result = ai_client._cleanup_json_response(complex_incomplete)

        # Should attempt recovery
        import json

        try:
            parsed = json.loads(result)
            # If recovery worked, should have basic structure
            assert "insights" in parsed or "summary" in parsed
        except json.JSONDecodeError:
            # If recovery failed, should return original
            assert result == complex_incomplete


class TestAIClientInsightExtraction:
    """Test insight extraction functionality."""

    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            api_key="sk-test_key_123456", model="gpt-4"  # pragma: allowlist secret
        )

    def test_extract_insights_bullet_points(self, ai_client):
        """Test extracting insights from bullet point format."""
        analysis_text = """Based on the analysis:

• Login issues reported by 45% of customers
• Billing confusion in 30% of conversations
• Feature requests for dark mode mentioned 5 times
- Password reset flow needs improvement
* Mobile app crashes affecting iOS users"""

        insights = ai_client._extract_insights(analysis_text)

        assert len(insights) == 5
        assert "Login issues reported by 45% of customers" in insights
        assert "Billing confusion in 30% of conversations" in insights
        assert "Feature requests for dark mode mentioned 5 times" in insights
        assert "Password reset flow needs improvement" in insights
        assert "Mobile app crashes affecting iOS users" in insights

    def test_extract_insights_no_bullets(self, ai_client):
        """Test extracting insights when no bullet points found."""
        analysis_text = """This is a regular paragraph without bullet points.
It contains insights but they are not formatted properly.
No structured list format here."""

        insights = ai_client._extract_insights(analysis_text)

        assert len(insights) == 0

    def test_extract_insights_limit_five(self, ai_client):
        """Test that insights are limited to 5 items."""
        analysis_text = """
• First insight
• Second insight
• Third insight
• Fourth insight
• Fifth insight
• Sixth insight (should be excluded)
• Seventh insight (should be excluded)
"""

        insights = ai_client._extract_insights(analysis_text)

        assert len(insights) == 5
        assert "Sixth insight (should be excluded)" not in insights
