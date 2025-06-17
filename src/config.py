"""Configuration management for Ask-Intercom."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Config(BaseModel):
    """Application configuration."""

    intercom_token: str = Field(..., description="Intercom access token")
    openai_key: str = Field(..., description="OpenAI API key")
    intercom_app_id: str = Field(
        default="",
        description="Intercom app/workspace ID for generating conversation URLs",
    )
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    max_conversations: int = Field(
        default=50, description="Max conversations to analyze"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    model_config = ConfigDict(
        env_file=[".env", str(Path(__file__).parent.parent / ".env")],
        env_file_encoding="utf-8",
    )

    @field_validator("intercom_token")
    @classmethod
    def validate_intercom_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Invalid Intercom access token")
        return v

    @field_validator("openai_key")
    @classmethod
    def validate_openai_key(cls, v):
        if not v or not v.startswith(("sk-", "pk-")):
            raise ValueError("Invalid OpenAI API key")
        return v

    @field_validator("intercom_app_id")
    @classmethod
    def validate_intercom_app_id(cls, v):
        # Allow empty string - conversation links will be disabled
        if v and len(v) < 5:
            raise ValueError("Invalid Intercom app ID")
        return v

    @field_validator("max_conversations")
    @classmethod
    def validate_max_conversations(cls, v):
        if v <= 0 or v > 200:
            raise ValueError("max_conversations must be between 1 and 200")
        return v

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Find the .env file - check current directory and project root
        env_paths = [
            Path.cwd() / ".env",  # Current working directory
            Path(__file__).parent.parent
            / ".env",  # Project root (one level up from src/)
        ]

        # Load from the first .env file found
        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                break
        else:
            # Fallback - try to load without specifying path
            load_dotenv()

        return cls(
            intercom_token=os.getenv("INTERCOM_ACCESS_TOKEN", ""),
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            intercom_app_id=os.getenv(
                "INTERCOM_APP_ID", ""
            ),  # Optional - will be fetched dynamically if not provided
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            max_conversations=int(os.getenv("MAX_CONVERSATIONS", "50")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

    def validate(self) -> None:
        """Validate the configuration."""
        # This will raise ValidationError if invalid
        self.__class__.model_validate(self.model_dump())
