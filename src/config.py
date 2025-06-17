"""Configuration management for Ask-Intercom."""

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class Config(BaseModel):
    """Application configuration."""

    intercom_token: str = Field(..., description="Intercom access token")
    openai_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    max_conversations: int = Field(
        default=50, description="Max conversations to analyze"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("intercom_token")
    def validate_intercom_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Invalid Intercom access token")
        return v

    @validator("openai_key")
    def validate_openai_key(cls, v):
        if not v or not v.startswith(("sk-", "pk-")):
            raise ValueError("Invalid OpenAI API key")
        return v

    @validator("max_conversations")
    def validate_max_conversations(cls, v):
        if v <= 0 or v > 200:
            raise ValueError("max_conversations must be between 1 and 200")
        return v

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        load_dotenv()

        return cls(
            intercom_token=os.getenv("INTERCOM_ACCESS_TOKEN", ""),
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            max_conversations=int(os.getenv("MAX_CONVERSATIONS", "50")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
        )

    def validate(self) -> None:
        """Validate the configuration."""
        # This will raise ValidationError if invalid
        self.__class__.parse_obj(self.dict())
