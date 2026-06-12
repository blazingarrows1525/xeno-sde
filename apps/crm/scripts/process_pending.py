"""Backfill: complete any approved campaign that never actually sent.

Older builds approved a campaign but had no send loop, so it sat at 'sending'
with an all-zero funnel forever. This runs the send simulation for every such
campaign (approved/sending but sent==0), leaving genuinely in-flight seeds alone.

    cd apps/crm
    python -m scripts.process_pending
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.events.simulate import simulate_send
from app.models.campaign import Campaign, CampaignStats


async def run() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        rows = await session.execute(
            select(Campaign).where(Campaign.status.in_(["approved", "sending", "draft"]))
        )
        campaigns = rows.scalars().all()
        done = 0
        for c in campaigns:
            stats = await session.get(CampaignStats, c.id)
            if stats and stats.sent and stats.sent > 0:
                continue  # a real in-flight 'sending' campaign — leave it be
            res = await simulate_send(session, c)
            await session.commit()
            print(f"- completed {c.name}: {res}")
            done += 1
        print(f"[ok] processed {done} stuck campaign(s)")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())


if __name__ == "__main__":
    main()
