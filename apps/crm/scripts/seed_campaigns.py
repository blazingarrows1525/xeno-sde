"""Seed realistic campaigns + stats (+ a sample of messages/events).

Gives the Campaigns and Insights pages real data: per-campaign funnels, channel ROI,
and a calibration curve whose predicted-vs-actual ROAS gap narrows over time (the agent
"learning"). Run after the customer seed:

    cd apps/crm
    python -m scripts.seed_campaigns --wipe
"""
import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.db import get_sessionmaker
from app.events.economics import value_spread
from app.models.campaign import Campaign, CampaignStats, CommunicationEvent, Message
from app.models.customer import Customer, Order


def _money(x: float) -> Decimal:
    return Decimal(str(round(x, 2)))


# name, channel, goal, status, days_ago, audience, predicted_roas, actual_roas, convert_rate, aov(INR)
CAMPAIGNS = [
    ("Win-back · 60-day dormant", "whatsapp", "Bring back customers who haven't ordered in 60 days", "completed", 40, 52, 5.2, 3.9, 0.085, 2600),
    ("VIP early access · new drop", "email", "Show new arrivals to high-LTV repeat buyers", "completed", 31, 38, 6.0, 5.1, 0.07, 3200),
    ("First-to-second order nudge", "sms", "Convert one-time buyers into repeat customers", "completed", 23, 60, 6.4, 6.0, 0.06, 1900),
    ("Festive offer · high-LTV", "whatsapp", "Reward top spenders before the festive season", "completed", 13, 45, 7.1, 6.8, 0.11, 3000),
    ("Replenishment reminder", "email", "Nudge customers who are due for a re-order", "sending", 4, 48, 6.9, 6.7, 0.09, 2400),
    ("New arrivals · VIP preview", "whatsapp", "Preview the new collection to top 10% spenders", "pending_approval", 1, 41, 7.3, 0.0, 0.10, 3100),
]

CHANNEL_COST = {"whatsapp": 0.85, "sms": 0.30, "email": 0.10}  # per message, INR


async def seed(wipe: bool, seed_value: int) -> None:
    random.seed(seed_value)
    now = datetime.now(timezone.utc)
    sm = get_sessionmaker()

    async with sm() as session:
        if wipe:
            # Attributed orders reference campaigns via SET NULL, so clear them explicitly first.
            await session.execute(delete(Order).where(Order.source == "campaign"))
            await session.execute(delete(Campaign))  # cascades to stats/messages/events
            await session.commit()
            print("- wiped existing campaigns")

        rows = await session.execute(
            select(Customer.id, Customer.first_name, Customer.phone_e164, Customer.email).limit(150)
        )
        customers = rows.all()

        for (name, channel, goal, status, days_ago, audience,
             pred_roas, actual_roas, conv, aov) in CAMPAIGNS:
            created = now - timedelta(days=days_ago)

            if status == "pending_approval":
                sent = 0
            elif status == "sending":
                sent = int(audience * 0.6)
            else:
                sent = audience

            delivered = int(sent * 0.93)
            opened = int(delivered * 0.72)
            read = int(opened * 0.85)
            clicked = int(delivered * 0.21)
            converted = int(sent * conv)
            failed = sent - delivered
            # Varied per-order values (not a flat AOV); revenue is their sum so it equals
            # SUM(attributed orders) for this campaign.
            order_values = [value_spread(aov, random) for _ in range(converted)]
            revenue = sum(order_values, Decimal("0"))
            send_cost = (revenue / Decimal(str(actual_roas))) if actual_roas > 0 else Decimal(str(sent * CHANNEL_COST[channel]))

            predicted = {
                "audience": audience,
                "roas": pred_roas,
                "convertRate": round(conv * 1.05, 4),
                "deliveredRate": 0.94,
                "openRate": 0.75,
                "clickRate": 0.22,
                "revenue": int(audience * conv * 1.05 * aov),
            }

            campaign = Campaign(
                name=name, channel=channel, goal_text=goal, status=status,
                predicted_kpis=predicted, created_at=created,
                approved_by=("operator" if status in ("completed", "sending") else None),
                approved_at=(created + timedelta(hours=1) if status in ("completed", "sending") else None),
                launched_at=(created + timedelta(hours=1) if status in ("completed", "sending") else None),
            )
            session.add(campaign)
            await session.flush()

            session.add(CampaignStats(
                campaign_id=campaign.id, sent=sent, delivered=delivered, failed=failed,
                opened=opened, read=read, clicked=clicked, converted=converted,
                revenue=_money(revenue), send_cost=_money(send_cost), updated_at=created,
            ))

            # A sample of messages with terminal states matching the funnel, for the
            # campaign-detail timeline + variant breakdown.
            if sent > 0 and customers:
                pool = (
                    ["converted"] * converted
                    + ["clicked"] * max(0, clicked - converted)
                    + ["opened"] * max(0, opened - clicked)
                    + ["delivered"] * max(0, delivered - opened)
                    + ["failed"] * failed
                )
                random.shuffle(pool)
                msgs = []
                for i, state in enumerate(pool[:28]):
                    cust = random.choice(customers)
                    recipient = cust.phone_e164 if channel in ("whatsapp", "sms") else cust.email
                    msgs.append(Message(
                        campaign_id=campaign.id, customer_id=cust.id,
                        variant=random.choice(["A", "B"]), channel=channel,
                        recipient=recipient or "n/a",
                        rendered_body=f"Hi {cust.first_name or 'there'}, a little something for you…",
                        current_state=state, last_sequence=1,
                        idempotency_key=f"seed-{campaign.id}-{i}",
                        attributed_revenue=(value_spread(aov, random) if state == "converted" else _money(0)),
                        created_at=created,
                    ))
                session.add_all(msgs)
                await session.flush()
                session.add_all([
                    CommunicationEvent(
                        message_id=m.id, event_type=m.current_state, sequence=1,
                        occurred_at=created + timedelta(minutes=random.randint(1, 300)),
                    )
                    for m in msgs
                ])

            # Real attributed orders backing this campaign's revenue — the source of truth for
            # ROAS, queryable as "which orders came from this campaign".
            if converted > 0 and customers:
                session.add_all([
                    Order(
                        customer_id=random.choice(customers).id,
                        external_id=f"seed-conv-{campaign.id}-{k}",
                        amount=val, currency="INR", status="placed",
                        ordered_at=created + timedelta(minutes=random.randint(1, 300)),
                        campaign_id=campaign.id, source="campaign",
                    )
                    for k, val in enumerate(order_values)
                ])

            await session.commit()
            print(f"- {name}: sent={sent} converted={converted} revenue={int(revenue)}")

    print("[ok] seeded campaigns")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    p = argparse.ArgumentParser(description="Seed Kairos with realistic campaigns + stats.")
    p.add_argument("--wipe", action="store_true", help="delete existing campaigns first")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    asyncio.run(seed(args.wipe, args.seed))


if __name__ == "__main__":
    main()
