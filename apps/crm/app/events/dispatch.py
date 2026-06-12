"""Outbound dispatch — fan a campaign out to per-recipient messages and hand them to the
Channel Service.

This is the CRM half of the two-service send loop the brief asks for. On approval we:

1. create one ``messages`` row per recipient (state ``queued``, with a stable
   ``idempotency_key`` so a resend can't double-fire), then
2. POST the batch to the Channel Service's ``/v1/send`` with a ``callback_url`` pointing at
   our own ``/v1/receipts``.

The Channel Service then simulates each message's lifecycle and POSTs signed event batches
back, which roll up into ``campaign_stats`` — so every number on the campaign page comes
from a real callback, not an in-process shortcut.

Scope tradeoff: at demo scale we cap the fan-out (``settings.send_cap``) and POST in batches
from the request path. At 100k+ this becomes a queue-backed outbound worker sharded by
campaign (blueprint §14); the message row + idempotency key are the seam that makes that
swap mechanical.
"""
from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.campaign import Campaign, Message
from app.models.customer import Customer

_BODY = "Hi {name}, a little something picked for you — take a look."
_BATCH = 100


def to_send_payload(messages: list[Message], callback_url: str) -> dict:
    """Pure CRM→Channel ``/v1/send`` body builder (unit-tested without a DB)."""
    return {
        "messages": [
            {
                "message_id": str(m.id),
                "campaign_id": str(m.campaign_id),
                "customer_id": str(m.customer_id),
                "channel": m.channel,
                "recipient": m.recipient,
                "body": m.rendered_body,
                "idempotency_key": m.idempotency_key,
            }
            for m in messages
        ],
        "callback_url": callback_url,
    }


async def build_messages(session: AsyncSession, campaign: Campaign, cap: int) -> list[Message]:
    """Create queued ``Message`` rows for the campaign's audience and flush to assign PKs.

    Audience here is the most-engaged slice of the real customer base (deterministic order),
    capped for the hosted demo. The flushed message ``id`` is what the channel echoes back on
    every callback, so it must exist before we dispatch.
    """
    rows = (
        await session.execute(
            select(
                Customer.id,
                Customer.first_name,
                Customer.phone_e164,
                Customer.email,
            )
            .order_by(Customer.total_orders.desc(), Customer.created_at.asc())
            .limit(cap)
        )
    ).all()

    channel = campaign.channel
    messages = [
        Message(
            campaign_id=campaign.id,
            customer_id=cust.id,
            variant="A" if i % 2 == 0 else "B",
            channel=channel,
            recipient=(cust.phone_e164 if channel in ("whatsapp", "sms") else cust.email) or "n/a",
            rendered_body=_BODY.format(name=cust.first_name or "there"),
            current_state="queued",
            last_sequence=0,
            idempotency_key=f"{campaign.id}:{cust.id}",
        )
        for i, cust in enumerate(rows)
    ]
    session.add_all(messages)
    await session.flush()  # assign message_id PKs before they're sent to the channel
    return messages


async def fan_out(session: AsyncSession, campaign: Campaign) -> list[Message]:
    """Create the campaign's queued messages and align its predicted audience to the real send.

    The caller commits these **before** dispatching, so the messages are visible by the time
    the channel's first callbacks arrive (otherwise early events would hit uncommitted rows and
    be dropped as orphans).
    """
    messages = await build_messages(session, campaign, settings.send_cap)

    pred = dict(campaign.predicted_kpis or {})
    pred["audience"] = len(messages)
    pred.setdefault("roas", 6.0)
    pred.setdefault("deliveredRate", 0.93)
    pred.setdefault("openRate", 0.72)
    pred.setdefault("clickRate", 0.21)
    pred.setdefault("convertRate", 0.09)
    campaign.predicted_kpis = pred
    return messages


def callback_url() -> str:
    return settings.crm_public_url.rstrip("/") + "/v1/receipts"


async def send_to_channel(messages: list[Message]) -> bool:
    """POST the batch to the Channel Service. False if it's cold/unreachable (caller falls back)."""
    if not messages:
        return False
    payload_messages = to_send_payload(messages, callback_url())["messages"]
    url = settings.channel_service_url.rstrip("/") + "/v1/send"
    try:
        async with httpx.AsyncClient(timeout=settings.channel_send_timeout) as client:
            for i in range(0, len(payload_messages), _BATCH):
                resp = await client.post(
                    url,
                    json={"messages": payload_messages[i : i + _BATCH], "callback_url": callback_url()},
                )
                if resp.status_code not in (200, 202):
                    return False
        return True
    except httpx.HTTPError:
        return False
