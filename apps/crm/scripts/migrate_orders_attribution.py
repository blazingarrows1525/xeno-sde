"""One-off, idempotent migration: add campaign-attribution columns to ``orders``.

Schema is otherwise managed by SQLAlchemy ``create_all``, which creates missing *tables* but
not missing *columns* on a table that already exists. A database created before attribution
existed therefore needs these three columns added. ``ADD COLUMN IF NOT EXISTS`` makes this safe
to run repeatedly and a no-op once applied. Fresh databases get the columns straight from the
model via ``create_all`` and never need this.

    cd apps/crm
    python -m scripts.migrate_orders_attribution
"""
import asyncio
import sys

from sqlalchemy import text

from app.core.db import get_engine

DDL = [
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS campaign_id uuid "
    "REFERENCES campaigns(id) ON DELETE SET NULL",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS attributed_message_id uuid "
    "REFERENCES messages(id) ON DELETE SET NULL",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS source varchar NOT NULL DEFAULT 'organic'",
    "CREATE INDEX IF NOT EXISTS ix_orders_campaign_id ON orders (campaign_id)",
]


async def main() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        for stmt in DDL:
            await conn.execute(text(stmt))
            print("ok:", stmt[: stmt.find("IF NOT EXISTS")].strip(), "…")
    await engine.dispose()
    print("[ok] orders attribution migration applied")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
