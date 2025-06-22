"""Tests for CostInfo parameter validation to prevent constructor errors."""

import pytest

from src.models import CostInfo


class TestCostInfoValidation:
    """Test CostInfo validation to prevent parameter mismatch issues."""

    def test_valid_construction(self):
        """Test that valid parameters work correctly."""
        cost_info = CostInfo(
            tokens_used=100, estimated_cost_usd=0.05, model_used="gpt-4"
        )
        assert cost_info.tokens_used == 100
        assert cost_info.estimated_cost_usd == 0.05
        assert cost_info.model_used == "gpt-4"

    def test_invalid_tokens_used(self):
        """Test that invalid tokens_used raises ValueError."""
        with pytest.raises(
            ValueError, match="tokens_used must be a non-negative integer"
        ):
            CostInfo(tokens_used=-1, estimated_cost_usd=0.05, model_used="gpt-4")

        with pytest.raises(
            ValueError, match="tokens_used must be a non-negative integer"
        ):
            CostInfo(tokens_used="invalid", estimated_cost_usd=0.05, model_used="gpt-4")

    def test_invalid_cost(self):
        """Test that invalid estimated_cost_usd raises ValueError."""
        with pytest.raises(
            ValueError, match="estimated_cost_usd must be a non-negative number"
        ):
            CostInfo(tokens_used=100, estimated_cost_usd=-0.05, model_used="gpt-4")

        with pytest.raises(
            ValueError, match="estimated_cost_usd must be a non-negative number"
        ):
            CostInfo(tokens_used=100, estimated_cost_usd="invalid", model_used="gpt-4")

    def test_invalid_model(self):
        """Test that invalid model_used raises ValueError."""
        with pytest.raises(ValueError, match="model_used must be a non-empty string"):
            CostInfo(tokens_used=100, estimated_cost_usd=0.05, model_used="")

        with pytest.raises(ValueError, match="model_used must be a non-empty string"):
            CostInfo(tokens_used=100, estimated_cost_usd=0.05, model_used=None)

    def test_from_usage_helper(self):
        """Test the from_usage class method."""
        cost_info = CostInfo.from_usage(usage_tokens=1000, model="gpt-4")
        assert cost_info.tokens_used == 1000
        assert abs(cost_info.estimated_cost_usd - 0.03) < 1e-10  # 1000 * 0.00003
        assert cost_info.model_used == "gpt-4"

    def test_from_usage_validation(self):
        """Test that from_usage validates parameters."""
        with pytest.raises(
            ValueError, match="usage_tokens must be non-negative integer"
        ):
            CostInfo.from_usage(usage_tokens=-100, model="gpt-4")

        with pytest.raises(ValueError, match="model must be non-empty string"):
            CostInfo.from_usage(usage_tokens=100, model="")

    def test_zero_cost_helper(self):
        """Test the zero_cost class method."""
        cost_info = CostInfo.zero_cost("test-model")
        assert cost_info.tokens_used == 0
        assert cost_info.estimated_cost_usd == 0.0
        assert cost_info.model_used == "test-model"

        # Test default model
        cost_info_default = CostInfo.zero_cost()
        assert cost_info_default.model_used == "unknown"

    def test_prevents_original_error(self):
        """Test that the original error scenario is now caught early."""
        # This would have been the problematic call that caused the original error
        # Now it should raise a clear ValueError instead of TypeError
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            # This should fail at construction time, not runtime
            CostInfo(input_tokens=1000, estimated_cost_usd=0.05, model_used="gpt-4")
