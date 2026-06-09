"""Kairos CRM — FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import segments
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(segments.router, prefix="/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "kairos-crm", "env": settings.environment}
