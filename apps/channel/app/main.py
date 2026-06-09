"""Kairos Channel Service — accepts sends, simulates the lifecycle, calls receipts back."""
from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.delivery import DEAD_LETTERS, run_lifecycle
from app.schemas import SendRequest
from app.simulator import plan_lifecycle
from app.store import ChannelStore

store = ChannelStore()
_runtime = {"failure_rate": settings.default_failure_rate}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=5.0)
    yield
    await app.state.client.aclose()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.post("/v1/send", status_code=202)
async def send(req: SendRequest) -> dict:
    accepted = duplicates = 0
    provider_messages = []
    callback_url = req.callback_url or settings.crm_receipts_url

    for item in req.messages:
        record, created = store.register(item)
        provider_messages.append(
            {"message_id": item.message_id, "provider_message_id": record.provider_message_id}
        )
        if not created:
            duplicates += 1
            continue
        accepted += 1
        if settings.auto_deliver:
            plan = plan_lifecycle(item.channel, random.Random(), _runtime["failure_rate"])
            asyncio.create_task(
                run_lifecycle(
                    record,
                    plan,
                    client=app.state.client,
                    url=callback_url,
                    secret=settings.hmac_secret,
                    time_scale=settings.time_scale,
                    max_retries=settings.callback_max_retries,
                )
            )

    return {"accepted": accepted, "duplicates": duplicates, "provider_messages": provider_messages}


@app.get("/v1/messages/{provider_message_id}")
async def get_message(provider_message_id: str) -> dict:
    record = store.get(provider_message_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown provider_message_id")
    return record.as_dict()


class FailureRate(BaseModel):
    rate: float = Field(ge=0.0, le=1.0)


@app.post("/v1/admin/failure-rate")
async def set_failure_rate(body: FailureRate) -> dict:
    """Demo knob: change the injected delivery-failure rate live."""
    _runtime["failure_rate"] = body.rate
    return {"failure_rate": body.rate}


@app.get("/v1/admin/dead-letters")
async def dead_letters() -> dict:
    return {"count": len(DEAD_LETTERS), "items": DEAD_LETTERS[-50:]}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "kairos-channel"}
