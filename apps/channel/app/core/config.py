"""Channel Service settings with local-friendly defaults."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Kairos Channel Service"

    crm_receipts_url: str = "http://localhost:8000/v1/receipts"
    hmac_secret: str = "dev-secret-change-me"

    # Simulated delays are multiplied by this so a full funnel completes in seconds on a demo.
    time_scale: float = 0.1
    default_failure_rate: float = 0.08
    callback_max_retries: int = 5

    # Tests set this False to skip spawning background delivery tasks.
    auto_deliver: bool = True


settings = Settings()
