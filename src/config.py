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
        default=1000, description="Max conversations to analyze (safety limit)"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # MCP Configuration
    enable_mcp: bool = Field(default=False, description="Enable MCP client")
    mcp_server_url: str = Field(
        default="https://mcp.intercom.com/sse", description="MCP server endpoint"
    )
    mcp_oauth_client_id: str = Field(default="", description="MCP OAuth client ID")
    mcp_oauth_client_secret: str = Field(
        default="", description="MCP OAuth client secret"
    )
    mcp_timeout: int = Field(default=30, description="MCP connection timeout")

    # MCP Transport Configuration
    mcp_transport: str = Field(
        default="stdio",
        description="MCP transport type: stdio (local Docker) or http (external server)",
    )
    mcp_http_url: str = Field(
        default="", description="HTTP endpoint for external MCP server"
    )
    mcp_api_key: str = Field(
        default="", description="Bearer token for HTTP MCP authentication"
    )

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
        if not v or not (v.startswith(("sk-", "pk-")) or v.startswith("sk-proj-")):
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
        if v <= 0 or v > 10000:
            raise ValueError("max_conversations must be between 1 and 10000")
        return v

    @field_validator("mcp_transport")
    @classmethod
    def validate_mcp_transport(cls, v):
        if v not in ["stdio", "http"]:
            raise ValueError("mcp_transport must be either 'stdio' or 'http'")
        return v

    def model_post_init(self, __context) -> None:
        """Post-initialization validation for interdependent fields."""
        # Validate HTTP transport configuration
        if self.mcp_transport == "http":
            if not self.mcp_http_url:
                raise ValueError("MCP_HTTP_URL must be set when using HTTP transport")
            if not self.mcp_api_key:
                raise ValueError("MCP_API_KEY must be set when using HTTP transport")

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
            max_conversations=int(os.getenv("MAX_CONVERSATIONS", "1000")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            # MCP settings
            enable_mcp=os.getenv("ENABLE_MCP", "false").lower() == "true",
            mcp_server_url=os.getenv("MCP_SERVER_URL", "https://mcp.intercom.com/sse"),
            mcp_oauth_client_id=os.getenv("MCP_OAUTH_CLIENT_ID", ""),
            mcp_oauth_client_secret=os.getenv("MCP_OAUTH_CLIENT_SECRET", ""),
            mcp_timeout=int(os.getenv("MCP_TIMEOUT", "30")),
            # MCP Transport settings
            mcp_transport=os.getenv("MCP_TRANSPORT", "stdio"),
            mcp_http_url=os.getenv("MCP_HTTP_URL", ""),
            mcp_api_key=os.getenv("MCP_API_KEY", ""),
        )

    def validate(self) -> None:
        """Validate the configuration."""
        # This will raise ValidationError if invalid
        self.__class__.model_validate(self.model_dump())
