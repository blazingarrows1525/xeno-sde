"""Analytics endpoints — channel ROI, calibration, and summary stats."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.campaign import Campaign, CampaignStats
from app.models.customer import Customer

router = APIRouter(tags=["analytics"])


@router.get("/analytics/channel-roi")
async def channel_roi(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """ROAS by channel — the bar chart on the Insights page."""
    q = (
        select(
            Campaign.channel,
            func.sum(CampaignStats.revenue).label("revenue"),
            func.sum(CampaignStats.send_cost).label("cost"),
            func.count(Campaign.id).label("campaigns"),
            func.sum(CampaignStats.sent).label("sent"),
            func.sum(CampaignStats.delivered).label("delivered"),
            func.sum(CampaignStats.converted).label("converted"),
        )
        .join(CampaignStats, CampaignStats.campaign_id == Campaign.id)
        .group_by(Campaign.channel)
    )
    rows = await session.execute(q)
    result = []
    for r in rows:
        cost = float(r.cost) if r.cost else 0
        rev = float(r.revenue) if r.revenue else 0
        roas = round(rev / cost, 2) if cost > 0 else 0
        sent = r.sent or 0
        result.append({
            "channel": r.channel,
            "revenue": rev,
            "cost": cost,
            "roas": roas,
            "campaigns": r.campaigns,
            "sent": sent,
            "delivered": r.delivered or 0,
            "converted": r.converted or 0,
        })
    # Best ROAS first — the Insights chart highlights the top channel.
    result.sort(key=lambda x: x["roas"], reverse=True)
    return result


@router.get("/analytics/calibration")
async def calibration(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Predicted vs actual ROAS per campaign — the calibration line chart.

    Only includes campaigns that have both predicted KPIs and actual stats.
    """
    q = (
        select(Campaign, CampaignStats)
        .join(CampaignStats, CampaignStats.campaign_id == Campaign.id)
        .where(Campaign.predicted_kpis.isnot(None))
        .where(CampaignStats.sent > 0)
        .order_by(Campaign.created_at)
    )
    rows = await session.execute(q)
    points = []
    for c, s in rows:
        cost = float(s.send_cost) if s.send_cost else 0
        actual_roas = round(float(s.revenue) / cost, 2) if cost > 0 else 0
        predicted_roas = (c.predicted_kpis or {}).get("roas", 0)
        points.append({
            "campaign": c.name,
            "predicted": predicted_roas,
            "actual": actual_roas,
        })
    return points


@router.get("/analytics/summary")
async def summary_stats(session: AsyncSession = Depends(get_session)) -> dict:
    """Aggregate stats for the Insights top cards."""
    total_cust = await session.scalar(select(func.count(Customer.id))) or 0
    total_campaigns = await session.scalar(select(func.count(Campaign.id))) or 0

    agg = await session.execute(
        select(
            func.coalesce(func.sum(CampaignStats.sent), 0).label("sent"),
            func.coalesce(func.sum(CampaignStats.converted), 0).label("converted"),
            func.coalesce(func.sum(CampaignStats.revenue), 0).label("revenue"),
            func.coalesce(func.sum(CampaignStats.send_cost), 0).label("cost"),
        )
    )
    row = agg.first()
    total_cost = float(row.cost) if row else 0
    total_rev = float(row.revenue) if row else 0

    return {
        "total_customers": total_cust,
        "total_campaigns": total_campaigns,
        "total_sent": row.sent if row else 0,
        "total_converted": row.converted if row else 0,
        "total_revenue": total_rev,
        "avg_roas": round(total_rev / total_cost, 2) if total_cost > 0 else 0,
    }
