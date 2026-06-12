"""Receipt callback endpoint — the Channel Service POSTs delivery events here.

This is the CRM end of the two-service loop. The channel signs each batch with HMAC-SHA256;
we verify it, then fold every event through the pure state machine:

1. Verify the signature over the raw body (one signature per batch).
2. For each event, ``decide(current_state, last_sequence, event_type, sequence)``:
   - ``advance`` → move ``Message.current_state``, append the event, roll up ``CampaignStats``.
   - ``stale``   → duplicate / out-of-order: counted, never regresses state (idempotent).
   - ``illegal`` → impossible transition / unknown type: counted, ignored.
3. ``sent`` accrues per-message send cost; ``converted`` books a real, campaign-attributed
   ``orders`` row (with the value the channel reports) and rolls its amount into revenue — so
   ROAS on the campaign page is computed from real orders, not a stored guess.
4. When every dispatched message has hit its terminal event, the campaign flips to ``completed``.

We always return 2xx for a well-formed batch (even an all-duplicate one) so the channel's
retry/backoff only fires on genuine server faults — matching its delivery contract.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.events.attribution import build_attributed_order, conversion_amount
from app.events.economics import CHANNEL_COST, money
from app.events.state_machine import decide
from app.models.campaign import Campaign, CampaignStats, CommunicationEvent, Message

_COUNTERS = ("sent", "delivered", "failed", "opened", "read", "clicked", "converted")


def _zero_deltas() -> dict:
    d: dict = {k: 0 for k in _COUNTERS}
    d["revenue"] = Decimal("0")
    d["send_cost"] = Decimal("0")
    return d

router = APIRouter(tags=["receipts"])


class ReceiptEvent(BaseModel):
    message_id: str
    event_type: str
    sequence: int
    occurred_at: datetime
    provider_message_id: str | None = None
    terminal: bool = False
    value: float | None = None  # order value reported on a `converted` event
    payload: dict | None = None


class ReceiptBatch(BaseModel):
    events: list[ReceiptEvent]


# ── HMAC verification ────────────────────────────────────────────────────

def _verify_hmac(body: bytes, signature: str | None) -> None:
    """Verify the channel's HMAC-SHA256 signature over the raw request body.

    The channel sends ``X-Signature: sha256=<hex>``; we accept the prefixed or a bare-hex
    form so either signer convention validates.
    """
    if not signature:
        raise HTTPException(401, "Missing X-Signature header")
    provided = signature.split("=", 1)[1] if "=" in signature else signature
    expected = hmac.new(settings.receipt_hmac_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(401, "Invalid signature")


# ── route ────────────────────────────────────────────────────────────────

@router.post("/receipts")
async def receive_receipts(
    request: Request,
    batch: ReceiptBatch,
    session: AsyncSession = Depends(get_session),
    x_signature: str | None = Header(None),
) -> dict:
    body = await request.body()
    _verify_hmac(body, x_signature)

    accepted = duplicates = ignored = 0
    # Per-campaign stat deltas, applied once at the end as atomic SQL increments. Every
    # message's callbacks hit the *same* campaign_stats row, so a Python read-modify-write
    # would lose updates under the concurrent callback fan-in; `col = col + delta` in SQL
    # serializes on the row lock and stays correct.
    deltas: dict[uuid.UUID, dict] = defaultdict(_zero_deltas)
    settled_campaigns: set[uuid.UUID] = set()

    for ev in batch.events:
        try:
            mid = uuid.UUID(ev.message_id)
        except ValueError:
            ignored += 1
            continue
        msg = await session.get(Message, mid)
        if msg is None:
            ignored += 1  # orphan callback for an unknown message — never crash the consumer
            continue

        decision = decide(
            current_state=msg.current_state,
            last_sequence=msg.last_sequence,
            event_type=ev.event_type,
            sequence=ev.sequence,
        )
        if decision.action == "stale":
            duplicates += 1
            continue
        if decision.action == "illegal":
            ignored += 1
            continue

        # Idempotent append: the unique (message_id, event_type, sequence) index is the
        # exactly-once gate. At-least-once delivery means the channel will re-POST events it
        # didn't get a 2xx for; ON CONFLICT DO NOTHING absorbs those (and any concurrent
        # retry that races past the `decide` check) without a 500.
        inserted = await session.execute(
            pg_insert(CommunicationEvent.__table__)
            .values(
                message_id=msg.id,
                event_type=ev.event_type,
                sequence=ev.sequence,
                payload={"terminal": True} if ev.terminal else ev.payload,
                occurred_at=ev.occurred_at,
            )
            .on_conflict_do_nothing(constraint="uq_event_idempotency")
        )
        if inserted.rowcount == 0:
            duplicates += 1  # already counted on a prior delivery — never double-count
            continue

        # Genuinely new event → advance the denormalized state and accrue the rollup.
        msg.current_state = decision.new_state or msg.current_state
        msg.last_sequence = decision.new_sequence or msg.last_sequence
        if ev.provider_message_id and not msg.provider_message_id:
            msg.provider_message_id = ev.provider_message_id

        d = deltas[msg.campaign_id]
        if ev.event_type in d:
            d[ev.event_type] += 1
        channel = msg.channel if msg.channel in CHANNEL_COST else "email"
        if ev.event_type == "sent":
            d["send_cost"] += money(CHANNEL_COST[channel])
        elif ev.event_type == "converted":
            # A conversion books a real, campaign-attributed order with the value the channel
            # reported; campaign revenue rolls up from these order rows, not a flat constant.
            amount = conversion_amount(ev.value, channel)
            msg.attributed_revenue = amount
            session.add(build_attributed_order(msg, amount, ev.occurred_at))
            d["revenue"] += amount
        if ev.terminal:
            settled_campaigns.add(msg.campaign_id)

        accepted += 1

    for campaign_id, d in deltas.items():
        await _apply_stats(session, campaign_id, d)
    # A campaign can only finish when a message hits its terminal event, so only check then.
    for campaign_id in settled_campaigns:
        await _maybe_complete(session, campaign_id)

    await session.commit()
    return {"accepted": accepted, "duplicates": duplicates, "ignored": ignored}


async def _apply_stats(session: AsyncSession, campaign_id: uuid.UUID, d: dict) -> None:
    """Fold a batch's deltas into campaign_stats with an atomic, lost-update-safe UPDATE."""
    result = await session.execute(
        update(CampaignStats)
        .where(CampaignStats.campaign_id == campaign_id)
        .values(
            sent=CampaignStats.sent + d["sent"],
            delivered=CampaignStats.delivered + d["delivered"],
            failed=CampaignStats.failed + d["failed"],
            opened=CampaignStats.opened + d["opened"],
            read=CampaignStats.read + d["read"],
            clicked=CampaignStats.clicked + d["clicked"],
            converted=CampaignStats.converted + d["converted"],
            revenue=CampaignStats.revenue + d["revenue"],
            send_cost=CampaignStats.send_cost + d["send_cost"],
            updated_at=func.now(),
        )
    )
    if result.rowcount == 0:  # no rollup row yet (shouldn't happen post-approval) — seed one
        session.add(
            CampaignStats(
                campaign_id=campaign_id,
                **{k: d[k] for k in _COUNTERS},
                revenue=d["revenue"],
                send_cost=d["send_cost"],
            )
        )


async def _maybe_complete(session: AsyncSession, campaign_id: uuid.UUID) -> None:
    """Flip a campaign to ``completed`` once every dispatched message has hit a terminal event.

    The channel marks the last event of each message's lifecycle ``terminal``; we persist that
    on the event and compare the count of settled messages to the dispatched total.
    """
    c = await session.get(Campaign, campaign_id)
    if c is None or c.status == "completed":
        return
    total = await session.scalar(
        select(func.count(Message.id)).where(Message.campaign_id == campaign_id)
    )
    if not total:
        return
    settled = await session.scalar(
        select(func.count(func.distinct(CommunicationEvent.message_id)))
        .select_from(CommunicationEvent)
        .join(Message, CommunicationEvent.message_id == Message.id)
        .where(Message.campaign_id == campaign_id)
        .where(CommunicationEvent.payload["terminal"].astext == "true")
    )
    if settled and settled >= total:
        c.status = "completed"
