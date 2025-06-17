"""Unit tests for configuration management."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Config


class TestConfigValidation:
    """Test Config validation logic."""

    def test_valid_config_creation(self):
        """Test creating config with valid values."""
        config = Config(
            intercom_token="valid_token_1234567890",
            openai_key="sk-valid_key_1234567890",  # pragma: allowlist secret
            model="gpt-4",
            max_conversations=50,
            debug=False,
        )

        assert config.intercom_token == "valid_token_1234567890"
        assert config.openai_key == "sk-valid_key_1234567890"
        assert config.model == "gpt-4"
        assert config.max_conversations == 50
        assert config.debug is False

    def test_invalid_intercom_token(self):
        """Test validation fails for invalid Intercom token."""
        with pytest.raises(ValidationError):
            Config(
                intercom_token="short",  # Too short
                openai_key="sk-valid_key",  # pragma: allowlist secret
                model="gpt-4",
            )

        with pytest.raises(ValidationError):
            Config(
                intercom_token="",  # Empty
                openai_key="sk-valid_key",  # pragma: allowlist secret
                model="gpt-4",
            )

    def test_invalid_openai_key(self):
        """Test validation fails for invalid OpenAI key."""
        with pytest.raises(ValidationError):
            Config(
                intercom_token="valid_token_1234567890",
                openai_key="invalid_key",  # Doesn't start with sk- or pk-
                model="gpt-4",
            )

        with pytest.raises(ValidationError):
            Config(
                intercom_token="valid_token_1234567890",
                openai_key="",  # Empty
                model="gpt-4",
            )

    def test_invalid_max_conversations(self):
        """Test validation fails for invalid max_conversations."""
        with pytest.raises(ValidationError):
            Config(
                intercom_token="valid_token_1234567890",
                openai_key="sk-valid_key",  # pragma: allowlist secret
                max_conversations=0,  # Too low
            )

        with pytest.raises(ValidationError):
            Config(
                intercom_token="valid_token_1234567890",
                openai_key="sk-valid_key",  # pragma: allowlist secret
                max_conversations=250,  # Too high
            )

    def test_default_values(self):
        """Test default values are applied correctly."""
        config = Config(
            intercom_token="valid_token_1234567890",
            openai_key="sk-valid_key_1234567890",  # pragma: allowlist secret
        )

        assert config.model == "gpt-4"  # Default
        assert config.max_conversations == 50  # Default
        assert config.debug is False  # Default

    def test_custom_model_values(self):
        """Test different model configurations."""
        config_gpt4 = Config(
            intercom_token="valid_token_1234567890",
            openai_key="sk-valid_key",
            model="gpt-4",
        )

        config_gpt35 = Config(
            intercom_token="valid_token_1234567890",
            openai_key="sk-valid_key",
            model="gpt-3.5-turbo",
        )

        assert config_gpt4.model == "gpt-4"
        assert config_gpt35.model == "gpt-3.5-turbo"


class TestConfigFromEnv:
    """Test Config.from_env() functionality."""

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "env_intercom_token_123456",
            "OPENAI_API_KEY": "sk-env_openai_key_123456",
            "OPENAI_MODEL": "gpt-4-turbo",
            "MAX_CONVERSATIONS": "75",
            "DEBUG": "true",
        },
    )
    def test_from_env_with_all_values(self):
        """Test loading config from environment variables."""
        config = Config.from_env()

        assert config.intercom_token == "env_intercom_token_123456"
        assert config.openai_key == "sk-env_openai_key_123456"
        assert config.model == "gpt-4-turbo"
        assert config.max_conversations == 75
        assert config.debug is True

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "env_token_123456",
            "OPENAI_API_KEY": "sk-env_key_123456",
            # Other values should use defaults
        },
        clear=True,
    )
    def test_from_env_with_defaults(self):
        """Test loading config with some defaults."""
        config = Config.from_env()

        assert config.intercom_token == "env_token_123456"
        assert config.openai_key == "sk-env_key_123456"
        assert config.model == "gpt-4"  # Default
        assert config.max_conversations == 50  # Default
        assert config.debug is False  # Default

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "",
            "OPENAI_API_KEY": "",
        },
        clear=True,
    )
    def test_from_env_with_missing_required(self):
        """Test that from_env fails with missing required values."""
        # from_env should fail with validation error
        with pytest.raises(ValidationError):
            Config.from_env()

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "valid_token_123456",
            "OPENAI_API_KEY": "sk-valid_key_123456",  # pragma: allowlist secret
            "DEBUG": "false",
        },
    )
    def test_debug_flag_parsing(self):
        """Test debug flag is parsed correctly."""
        config = Config.from_env()
        assert config.debug is False

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "valid_token_123456",
            "OPENAI_API_KEY": "sk-valid_key_123456",  # pragma: allowlist secret
            "DEBUG": "TRUE",  # Different case
        },
    )
    def test_debug_flag_case_insensitive(self):
        """Test debug flag parsing is case insensitive."""
        config = Config.from_env()
        assert config.debug is True

    @patch.dict(
        os.environ,
        {
            "INTERCOM_ACCESS_TOKEN": "valid_token_123456",
            "OPENAI_API_KEY": "sk-valid_key_123456",  # pragma: allowlist secret
            "MAX_CONVERSATIONS": "invalid",  # Invalid integer
        },
    )
    def test_invalid_max_conversations_from_env(self):
        """Test handling of invalid MAX_CONVERSATIONS from env."""
        with pytest.raises(ValueError):
            Config.from_env()


class TestConfigValidateMethod:
    """Test the validate() method."""

    def test_validate_with_valid_config(self):
        """Test validate() passes with valid config."""
        config = Config(
            intercom_token="valid_token_1234567890",
            openai_key="sk-valid_key_1234567890",  # pragma: allowlist secret
        )

        # Should not raise any exception
        config.validate()

    def test_validate_with_invalid_config(self):
        """Test validate() fails with invalid config."""
        # Test that creating invalid config raises ValidationError
        with pytest.raises(ValidationError):
            Config(
                intercom_token="short",  # Invalid - too short
                openai_key="invalid",  # Invalid - wrong format
                model="gpt-4",
                max_conversations=50,
                debug=False,
            )
