"""Application settings, loaded from environment with safe local defaults.

Defaults are chosen so the service boots and tests run without any external
dependency. Real values come from `.env` (see `.env.example`) in deployment.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kairos CRM"
    environment: str = "local"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kairos"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    planner_model: str = "claude-opus-4-8"
    bulk_model: str = "claude-haiku-4-5-20251001"

    channel_service_url: str = "http://localhost:8001"
    receipt_hmac_secret: str = "dev-secret-change-me"

    # Safety rails for the agent
    agent_max_steps: int = 16
    agent_max_tokens: int = 120_000
    campaign_max_recipients: int = 50_000


settings = Settings()
