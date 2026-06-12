"""Campaign CRUD with approval gate + launch trigger."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_session
from app.events.dispatch import fan_out, send_to_channel
from app.events.simulate import simulate_send
from app.models.campaign import Campaign, CampaignStats, CommunicationEvent, Message

router = APIRouter(tags=["campaigns"])


# ── schemas ──────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str
    channel: str
    segment_id: str | None = None
    goal_text: str | None = None
    plan: dict[str, Any] | None = None
    predicted_kpis: dict[str, Any] | None = None


class CampaignOut(BaseModel):
    id: str
    name: str
    channel: str
    status: str
    goal_text: str | None
    segment_id: str | None
    predicted_kpis: dict[str, Any] | None
    approved_by: str | None
    created_at: str
    stats: dict[str, Any] | None = None


class ApproveRequest(BaseModel):
    approved_by: str = "operator"


class CampaignDetail(BaseModel):
    id: str
    name: str
    channel: str
    status: str
    goal_text: str | None
    plan: dict[str, Any] | None
    predicted_kpis: dict[str, Any] | None
    approved_by: str | None
    created_at: str
    stats: dict[str, Any] | None = None
    funnel: dict[str, int] | None = None
    timeline: list[dict[str, Any]] = []
    variants: list[dict[str, Any]] = []


# ── helpers ──────────────────────────────────────────────────────────────

def _stats_dict(s: CampaignStats | None) -> dict[str, Any] | None:
    if s is None:
        return None
    return {
        "sent": s.sent,
        "delivered": s.delivered,
        "failed": s.failed,
        "opened": s.opened,
        "read": s.read,
        "clicked": s.clicked,
        "converted": s.converted,
        "revenue": float(s.revenue),
        "send_cost": float(s.send_cost),
    }


# ── routes ───────────────────────────────────────────────────────────────

@router.post("/campaigns", response_model=CampaignOut, status_code=201)
async def create_campaign(
    req: CampaignCreate, session: AsyncSession = Depends(get_session)
) -> CampaignOut:
    campaign = Campaign(
        name=req.name,
        channel=req.channel,
        segment_id=uuid.UUID(req.segment_id) if req.segment_id else None,
        goal_text=req.goal_text,
        plan=req.plan,
        predicted_kpis=req.predicted_kpis,
        status="draft",
    )
    session.add(campaign)
    # Flush first so Postgres assigns the gen_random_uuid() PK, then attach the empty
    # stats row (its PK *is* the campaign id, so it can't be built before the flush).
    await session.flush()
    session.add(CampaignStats(campaign_id=campaign.id))
    await session.commit()
    await session.refresh(campaign)  # load the server-side created_at
    return CampaignOut(
        id=str(campaign.id),
        name=campaign.name,
        channel=campaign.channel,
        status=campaign.status,
        goal_text=campaign.goal_text,
        segment_id=str(campaign.segment_id) if campaign.segment_id else None,
        predicted_kpis=campaign.predicted_kpis,
        approved_by=campaign.approved_by,
        created_at=campaign.created_at.isoformat(),
    )


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignOut]:
    rows = await session.execute(
        select(Campaign).options(selectinload(Campaign.stats)).order_by(Campaign.created_at.desc())
    )
    return [
        CampaignOut(
            id=str(c.id),
            name=c.name,
            channel=c.channel,
            status=c.status,
            goal_text=c.goal_text,
            segment_id=str(c.segment_id) if c.segment_id else None,
            predicted_kpis=c.predicted_kpis,
            approved_by=c.approved_by,
            created_at=c.created_at.isoformat(),
            stats=_stats_dict(c.stats),
        )
        for c in rows.scalars()
    ]


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> CampaignDetail:
    c = await session.get(
        Campaign,
        uuid.UUID(campaign_id),
        options=[selectinload(Campaign.stats)],
    )
    if c is None:
        raise HTTPException(404, "Campaign not found")

    stats = _stats_dict(c.stats)
    funnel = {
        "sent": c.stats.sent if c.stats else 0,
        "delivered": c.stats.delivered if c.stats else 0,
        "opened": c.stats.opened if c.stats else 0,
        "read": c.stats.read if c.stats else 0,
        "clicked": c.stats.clicked if c.stats else 0,
        "converted": c.stats.converted if c.stats else 0,
        "failed": c.stats.failed if c.stats else 0,
    }

    # Recent timeline events (last 50)
    events_q = (
        select(
            CommunicationEvent.event_type,
            CommunicationEvent.occurred_at,
            Message.variant,
            Message.recipient,
        )
        .join(Message, CommunicationEvent.message_id == Message.id)
        .where(Message.campaign_id == uuid.UUID(campaign_id))
        .order_by(CommunicationEvent.occurred_at.desc())
        .limit(50)
    )
    events = await session.execute(events_q)
    timeline = [
        {
            "state": r.event_type,
            "at": r.occurred_at.isoformat(),
            "variant": r.variant,
            "customer": r.recipient,
        }
        for r in events
    ]

    # Variant-level aggregation
    variant_q = (
        select(
            Message.variant,
            func.count(Message.id).label("total"),
            func.sum(case((Message.current_state == "clicked", 1), else_=0)).label("clicked"),
            func.sum(case((Message.current_state == "converted", 1), else_=0)).label("converted"),
        )
        .where(Message.campaign_id == uuid.UUID(campaign_id))
        .group_by(Message.variant)
    )
    variants = await session.execute(variant_q)
    variant_list = [
        {"variant": r.variant, "total": r.total, "clicked": r.clicked, "converted": r.converted}
        for r in variants
    ]

    return CampaignDetail(
        id=str(c.id),
        name=c.name,
        channel=c.channel,
        status=c.status,
        goal_text=c.goal_text,
        plan=c.plan,
        predicted_kpis=c.predicted_kpis,
        approved_by=c.approved_by,
        created_at=c.created_at.isoformat(),
        stats=stats,
        funnel=funnel,
        timeline=timeline,
        variants=variant_list,
    )


@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignOut)
async def approve_campaign(
    campaign_id: str,
    req: ApproveRequest,
    session: AsyncSession = Depends(get_session),
) -> CampaignOut:
    """The human approval gate: record the approval, then launch through the channel.

    Approving *is* launching. We fan the campaign out to real per-recipient messages and
    dispatch them to the separate Channel Service; it simulates each lifecycle and calls
    back into ``/v1/receipts``, which rolls events up into stats — so the funnel fills in
    live and the campaign settles to 'completed' on its own.

    If the Channel Service is unreachable (e.g. a cold free-tier instance), we fall back to
    the deterministic in-process simulation so the campaign never stalls at 'sending'.
    """
    c = await session.get(Campaign, uuid.UUID(campaign_id))
    if c is None:
        raise HTTPException(404, "Campaign not found")
    if c.approved_by:
        raise HTTPException(409, "Already approved")

    now = datetime.now(timezone.utc)
    c.approved_by = req.approved_by
    c.approved_at = now
    c.launched_at = now
    c.status = "sending"

    # Zero the rollup so the live funnel climbs purely from real channel callbacks.
    stats = await session.get(CampaignStats, c.id)
    if stats is None:
        stats = CampaignStats(campaign_id=c.id)
        session.add(stats)
    for field in ("sent", "delivered", "failed", "opened", "read", "clicked", "converted"):
        setattr(stats, field, 0)
    stats.revenue = Decimal("0")
    stats.send_cost = Decimal("0")
    stats.updated_at = now

    # Phase 1: persist the queued messages and commit, so they're visible before the
    # channel's first callbacks land (otherwise early events hit uncommitted rows).
    messages = await fan_out(session, c)
    await session.commit()

    # Phase 2: hand the batch to the separate Channel Service. It simulates each lifecycle
    # and calls /v1/receipts back, which rolls the funnel up and settles the campaign.
    ok = await send_to_channel(messages)
    if not ok:
        # Channel cold/unreachable → deterministic in-process fallback (same tables/shapes),
        # so the campaign never stalls at 'sending'.
        for m in messages:
            await session.delete(m)
        await session.flush()
        await simulate_send(session, c)
        await session.commit()
    await session.refresh(c)

    return CampaignOut(
        id=str(c.id),
        name=c.name,
        channel=c.channel,
        status=c.status,
        goal_text=c.goal_text,
        segment_id=str(c.segment_id) if c.segment_id else None,
        predicted_kpis=c.predicted_kpis,
        approved_by=c.approved_by,
        created_at=c.created_at.isoformat(),
    )
