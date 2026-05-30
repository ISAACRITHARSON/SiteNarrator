"""SiteNarrator — Application configuration.

Loads environment variables and provides typed access
to all configuration values across the application.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── AWS ───────────────────────────────────────────
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # ─── Amazon Bedrock ────────────────────────────────
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250514"

    # ─── Amazon Bedrock AgentCore ──────────────────────
    agentcore_memory_id: str = ""
    agentcore_gateway_id: str = ""
    agentcore_policy_engine_id: str = ""

    # ─── Box ───────────────────────────────────────────
    box_client_id: str = ""
    box_client_secret: str = ""
    box_enterprise_id: str = ""
    box_root_folder_id: str = ""

    # ─── OpenWeatherMap ────────────────────────────────
    openweather_api_key: str = ""

    # ─── Application ───────────────────────────────────
    app_secret_key: str = "change-me-in-production"
    app_env: str = "development"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # ─── Email (AWS SES) ──────────────────────────────
    ses_sender_email: str = ""
    ses_region: str = "us-east-1"

    # ─── Observability ─────────────────────────────────
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "sitenarrator"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
