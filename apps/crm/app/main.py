"""Kairos CRM — FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent, analytics, campaigns, customers, receipts, segments
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

# Allow the Next.js frontend (dev + production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(segments.router, prefix="/v1")
app.include_router(customers.router, prefix="/v1")
app.include_router(campaigns.router, prefix="/v1")
app.include_router(receipts.router, prefix="/v1")
app.include_router(analytics.router, prefix="/v1")
app.include_router(agent.router, prefix="/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "kairos-crm", "env": settings.environment}
