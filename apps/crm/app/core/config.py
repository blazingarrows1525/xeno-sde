"""Application settings, loaded from environment with safe local defaults.

Defaults are chosen so the service boots and tests run without any external
dependency. Real values come from `.env` (see `.env.example`) in deployment.
"""
from __future__ import annotations

import ssl
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve apps/crm/.env from this file's location so settings load regardless of the
# process working directory (uvicorn, alembic, the preview launcher, deploys).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def normalize_database_url(raw: str) -> tuple[str, dict]:
    """Make a stock libpq/Neon connection string safe for SQLAlchemy's asyncpg driver.

    Hosted Postgres (Neon, Supabase, RDS) hands you a URL like
    ``postgresql://user:pass@host/db?sslmode=require``. asyncpg's DSN parser rejects
    ``sslmode``/``channel_binding`` (those are libpq-only), so we:

    * upgrade the scheme to ``postgresql+asyncpg://`` (idempotent),
    * pop the libpq-only query params, and
    * translate ``sslmode`` into an asyncpg ``ssl`` connect-arg (an SSLContext).

    Returns ``(url, connect_args)`` so callers can paste the provider string verbatim.
    """
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # asyncpg negotiates SCRAM channel binding itself

    connect_args: dict = {}
    if sslmode and sslmode != "disable":
        ctx = ssl.create_default_context()
        if sslmode in ("require", "prefer", "allow"):
            # libpq `require` = encrypt but don't verify the CA/hostname.
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    # Hosted Postgres often sits behind a transaction pooler (PgBouncer — e.g. Neon's
    # `-pooler` endpoint). Cached, named prepared statements break there, so make both
    # asyncpg and SQLAlchemy's dialect use unique, un-cached statement names.
    host = (parts.hostname or "").lower()
    if "pooler" in host or "pgbouncer" in host:
        connect_args["statement_cache_size"] = 0  # asyncpg: disable its statement cache
        connect_args["prepared_statement_cache_size"] = 0  # SQLAlchemy dialect cache off
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid4()}__"

    normalized = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    return normalized, connect_args


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    app_name: str = "Kairos CRM"
    environment: str = "local"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kairos"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    planner_model: str = "claude-opus-4-8"
    bulk_model: str = "claude-haiku-4-5-20251001"

    channel_service_url: str = "http://localhost:8001"
    receipt_hmac_secret: str = "dev-secret-change-me"

    # Comma-separated allowed CORS origins (the deployed web app). Any *.vercel.app
    # preview is additionally allowed via regex in main.py.
    cors_origins: str = "http://localhost:3000"

    # Safety rails for the agent
    agent_max_steps: int = 16
    agent_max_tokens: int = 120_000
    campaign_max_recipients: int = 50_000

    @property
    def sqlalchemy_url(self) -> str:
        """Async-driver URL with libpq-only params stripped (see normalize_database_url)."""
        return normalize_database_url(self.database_url)[0]

    @property
    def engine_connect_args(self) -> dict:
        """Driver connect-args (e.g. the SSL context for hosted Postgres)."""
        return normalize_database_url(self.database_url)[1]


settings = Settings()
