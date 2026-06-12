"""Play a campaign's send → receipt funnel forward and roll it up into stats.

Approving a campaign in the live app does more than flip a flag. It fans the
campaign out to its predicted audience, plays the delivery funnel forward with
realistic per-channel rates, writes a sample of messages + one terminal event
each (for the detail timeline and the per-variant breakdown), rolls everything
into ``campaign_stats``, and marks the campaign ``completed``.

The "actual" ROAS is drawn to land just under the agent's prediction, so the
Insights calibration chart keeps telling a believable story: the agent slightly
over-forecasts, then converges. The funnel ratios mirror ``scripts/seed_campaigns``
so a launched campaign is indistinguishable from the seeded historical ones.

``simulate_send`` is idempotent — a campaign whose stats already show sends is
returned untouched, so re-approval or a backfill pass can never double-count.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import Random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.economics import CHANNEL_AOV, CHANNEL_COST, draw_order_value, money as _money
from app.models.campaign import Campaign, CampaignStats, CommunicationEvent, Message
from app.models.customer import Customer, Order

SAMPLE_MESSAGES = 32  # messages materialized for the timeline / variant breakdown


async def simulate_send(session: AsyncSession, campaign: Campaign) -> dict:
    """Fan ``campaign`` out, persist its funnel, and mark it completed.

    Adds rows to the open session but does **not** commit — the caller owns the
    transaction. Returns a small summary of the simulated outcome.
    """
    stats = await session.get(CampaignStats, campaign.id)
    if stats is None:
        stats = CampaignStats(campaign_id=campaign.id)
        session.add(stats)
    if stats.sent and stats.sent > 0:
        return {"already_sent": True, "sent": stats.sent}

    # Deterministic per campaign, so a replay reproduces the same funnel.
    rng = Random(campaign.id.int & 0xFFFFFFFF)

    pred = dict(campaign.predicted_kpis or {})
    audience = int(pred.get("audience") or 50)
    predicted_roas = float(pred.get("roas") or 6.0)
    # A supplied convertRate is the agent's optimistic forecast; actuals run ~5% under it.
    raw_conv = pred.get("convertRate")
    conv_rate = (float(raw_conv) / 1.05) if raw_conv else 0.09
    conv_rate = max(0.03, min(conv_rate, 0.2))

    channel = campaign.channel if campaign.channel in CHANNEL_COST else "email"

    sent = max(1, audience)
    delivered = round(sent * 0.93)
    opened = round(delivered * 0.72)
    read = round(opened * 0.85)
    clicked = round(delivered * 0.21)
    converted = min(round(sent * conv_rate), clicked)  # a conversion implies a click
    failed = sent - delivered

    # Each conversion books a real order with a varied value; revenue is their sum, so the
    # fallback holds the same SUM(orders) == revenue invariant as the live receipt loop.
    order_values = [draw_order_value(channel, rng) for _ in range(converted)]
    revenue = sum(order_values, Decimal("0"))
    actual_roas = predicted_roas * rng.uniform(0.80, 0.95)
    send_cost = (
        revenue / Decimal(str(actual_roas))
        if (converted > 0 and actual_roas > 0)
        else Decimal(str(sent * CHANNEL_COST[channel]))
    )

    now = datetime.now(timezone.utc)
    stats.sent = sent
    stats.delivered = delivered
    stats.failed = failed
    stats.opened = opened
    stats.read = read
    stats.clicked = clicked
    stats.converted = converted
    stats.revenue = _money(revenue)
    stats.send_cost = _money(send_cost)
    stats.updated_at = now

    # Backfill any predicted KPIs the proposal didn't carry, so the detail page's
    # predicted-vs-actual panel is fully populated rather than showing 0%.
    pred.setdefault("convertRate", round(conv_rate * 1.05, 4))
    pred.setdefault("deliveredRate", 0.94)
    pred.setdefault("openRate", 0.75)
    pred.setdefault("clickRate", 0.22)
    pred.setdefault("revenue", int(audience * conv_rate * 1.05 * CHANNEL_AOV[channel]))
    pred["audience"] = audience
    pred["roas"] = predicted_roas
    campaign.predicted_kpis = pred

    campaign.status = "completed"
    if campaign.approved_by is None:
        campaign.approved_by = "operator"
    if campaign.approved_at is None:
        campaign.approved_at = now
    campaign.launched_at = now

    # A sample of messages with terminal states matching the funnel, each with one
    # event — drives the campaign-detail timeline + per-variant aggregation.
    customers = (
        await session.execute(
            select(Customer.id, Customer.first_name, Customer.phone_e164, Customer.email).limit(120)
        )
    ).all()
    if customers:
        pool = (
            ["converted"] * converted
            + ["clicked"] * max(0, clicked - converted)
            + ["opened"] * max(0, opened - clicked)
            + ["delivered"] * max(0, delivered - opened)
            + ["failed"] * failed
        )
        rng.shuffle(pool)
        msgs = [
            Message(
                campaign_id=campaign.id,
                customer_id=cust.id,
                variant=rng.choice(["A", "B"]),
                channel=channel,
                recipient=(cust.phone_e164 if channel in ("whatsapp", "sms") else cust.email) or "n/a",
                rendered_body=f"Hi {cust.first_name or 'there'}, a little something for you…",
                current_state=state,
                last_sequence=1,
                idempotency_key=f"sim-{campaign.id}-{i}",
                attributed_revenue=(draw_order_value(channel, rng) if state == "converted" else _money(0)),
                created_at=now,
            )
            for i, state in enumerate(pool[:SAMPLE_MESSAGES])
            for cust in [rng.choice(customers)]
        ]
        session.add_all(msgs)
        await session.flush()
        session.add_all(
            [
                CommunicationEvent(
                    message_id=m.id,
                    event_type=m.current_state,
                    sequence=1,
                    occurred_at=now - timedelta(minutes=rng.randint(1, 240)),
                )
                for m in msgs
            ]
        )

    # Real, campaign-attributed orders — the same source of truth the live loop writes, so a
    # fallback-settled campaign is queryable the same way ("which orders came from this campaign").
    if converted > 0 and customers:
        session.add_all(
            [
                Order(
                    customer_id=rng.choice(customers).id,
                    external_id=f"sim-conv-{campaign.id}-{k}",
                    amount=val,
                    currency="INR",
                    status="placed",
                    ordered_at=now - timedelta(minutes=rng.randint(1, 240)),
                    campaign_id=campaign.id,
                    source="campaign",
                )
                for k, val in enumerate(order_values)
            ]
        )

    return {
        "sent": sent,
        "delivered": delivered,
        "converted": converted,
        "revenue": float(round(revenue, 2)),
        "roas": round(actual_roas, 2),
    }
