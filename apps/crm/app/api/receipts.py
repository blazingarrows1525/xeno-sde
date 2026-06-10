"""Receipt callback endpoint — Channel Service posts delivery events here.

The flow:
1. Channel Service signs the callback body with HMAC-SHA256
2. We verify the signature (reject 401 if invalid)
3. Feed the event into the state machine → decide(current_state, event_type, sequence)
4. If "advance": update Message + increment CampaignStats
5. If "stale" or "illegal": log and ignore (idempotent)
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.events.state_machine import decide
from app.models.campaign import CampaignStats, CommunicationEvent, Message

router = APIRouter(tags=["receipts"])


class ReceiptPayload(BaseModel):
    message_id: str
    event_type: str
    sequence: int
    occurred_at: datetime
    payload: dict | None = None


# ── HMAC verification ────────────────────────────────────────────────────

def _verify_hmac(body: bytes, signature: str | None) -> None:
    """Verify HMAC-SHA256 signature from Channel Service."""
    if not signature:
        raise HTTPException(401, "Missing X-Signature header")
    expected = hmac.new(
        settings.receipt_hmac_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid signature")


# ── route ────────────────────────────────────────────────────────────────

@router.post("/receipts", status_code=204)
async def receive_receipt(
    request: Request,
    receipt: ReceiptPayload,
    session: AsyncSession = Depends(get_session),
    x_signature: str | None = Header(None),
) -> None:
    """Process a delivery event callback from the Channel Service."""
    # 1. Verify HMAC
    body = await request.body()
    _verify_hmac(body, x_signature)

    # 2. Find the message
    msg = await session.get(Message, uuid.UUID(receipt.message_id))
    if msg is None:
        raise HTTPException(404, "Unknown message_id")

    # 3. Run the state machine
    decision = decide(
        current_state=msg.current_state,
        last_sequence=msg.last_sequence,
        event_type=receipt.event_type,
        sequence=receipt.sequence,
    )

    if decision.action == "stale":
        return  # duplicate or out-of-order → ignore
    if decision.action == "illegal":
        return  # log in production, ignore for now

    # 4. Advance the message state
    msg.current_state = receipt.event_type
    msg.last_sequence = receipt.sequence

    # 5. Record the event (uq_event_idempotency catches true dupes)
    event = CommunicationEvent(
        message_id=msg.id,
        event_type=receipt.event_type,
        sequence=receipt.sequence,
        payload=receipt.payload,
        occurred_at=receipt.occurred_at,
    )
    session.add(event)

    # 6. Increment campaign stats
    stats = await session.get(CampaignStats, msg.campaign_id)
    if stats is None:
        stats = CampaignStats(campaign_id=msg.campaign_id)
        session.add(stats)

    counter_field = receipt.event_type  # sent, delivered, failed, opened, read, clicked, converted
    if hasattr(stats, counter_field):
        setattr(stats, counter_field, getattr(stats, counter_field) + 1)

    await session.commit()
