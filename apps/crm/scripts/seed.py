"""Generate realistic, well-distributed shoppers + orders.

The goal is data that makes segments and analytics look *real* on camera: a healthy mix of
champions, loyal regulars, dormant win-back targets, and one-time buyers — with believable
recency, frequency and monetary spread.

Run once DATABASE_URL points at a Postgres:

    cd apps/crm
    python -m scripts.seed --customers 2000 --create-all     # bootstrap tables + data
    python -m scripts.seed --customers 5000 --wipe            # reseed against existing tables
"""
import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker
from sqlalchemy import delete

from app.core.db import create_all, get_sessionmaker
from app.models import Customer, Order, OrderItem

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad",
    "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Surat",
]

# (sku, product name, base price in INR)
CATALOG = [
    ("TEE-001", "Cotton Crew Tee", 799),
    ("DNM-014", "Slim-fit Jeans", 2499),
    ("SNK-220", "Canvas Sneakers", 1999),
    ("JKT-030", "Bomber Jacket", 3499),
    ("DRS-110", "Summer Dress", 1799),
    ("BAG-007", "Crossbody Bag", 1299),
    ("CAP-002", "Baseball Cap", 599),
    ("SCK-040", "Ankle Socks (3pk)", 399),
]

# persona -> (weight, recency_days range, num_orders range)
PERSONAS = {
    "champion":    (0.12, (0, 25),    (6, 20)),
    "loyal":       (0.18, (10, 45),   (3, 8)),
    "promising":   (0.15, (20, 60),   (1, 3)),
    "dormant":     (0.20, (60, 180),  (2, 6)),   # the win-back target
    "hibernating": (0.15, (180, 540), (1, 4)),
    "new":         (0.10, (0, 20),    (1, 1)),
    "one_timer":   (0.10, (40, 300),  (1, 1)),
}


def _pick_persona() -> str:
    names = list(PERSONAS)
    weights = [PERSONAS[n][0] for n in names]
    return random.choices(names, weights=weights, k=1)[0]


def _money(x: float) -> Decimal:
    return Decimal(str(round(x, 2)))


def _make_order(ext: str, ordered_at: datetime) -> tuple[Order, Decimal]:
    items: list[OrderItem] = []
    total = 0.0
    for _ in range(random.randint(1, 3)):
        sku, name, base = random.choice(CATALOG)
        qty = random.randint(1, 3)
        unit = round(base * random.uniform(0.85, 1.15), 2)  # small price variance
        total += unit * qty
        items.append(
            OrderItem(sku=sku, product_name=name, qty=qty, unit_price=_money(unit))
        )
    order = Order(
        external_id=ext,
        amount=_money(total),
        currency="INR",
        status="placed",
        ordered_at=ordered_at,
        items=items,
    )
    return order, _money(total)


def _make_customer(idx: int, fake: Faker, now: datetime) -> Customer:
    persona = _pick_persona()
    _, (rec_lo, rec_hi), (ord_lo, ord_hi) = PERSONAS[persona]

    last_offset = random.randint(rec_lo, rec_hi)
    num_orders = random.randint(ord_lo, ord_hi)
    signup_offset = min(last_offset + random.randint(15, 400), 900)
    last_order_at = now - timedelta(days=last_offset)
    signup_at = now - timedelta(days=signup_offset)

    # Spread order dates between signup and the last order; newest == last_order_at.
    offsets = sorted(
        {last_offset} | {random.randint(last_offset, signup_offset) for _ in range(num_orders - 1)},
        reverse=True,
    )
    orders: list[Order] = []
    total_spend = Decimal("0")
    for j, off in enumerate(offsets):
        order, amount = _make_order(f"O-{idx:05d}-{j}", now - timedelta(days=off))
        orders.append(order)
        total_spend += amount

    return Customer(
        external_id=f"C-{idx:05d}",
        first_name=fake.first_name(),
        email=fake.unique.email(),
        phone_e164=f"+9198{random.randint(10000000, 99999999)}",
        whatsapp_opt_in=random.random() < 0.70,
        email_opt_in=random.random() < 0.88,
        city=random.choice(CITIES),
        total_spend=total_spend,
        total_orders=len(orders),
        ltv=total_spend,
        last_order_at=last_order_at,
        created_at=signup_at,
        orders=orders,
    )


async def seed(n: int, wipe: bool, create: bool, seed_value: int) -> None:
    random.seed(seed_value)
    fake = Faker("en_IN")
    Faker.seed(seed_value)
    now = datetime.now(timezone.utc)

    if create:
        await create_all()
        print("-tables ensured")

    sm = get_sessionmaker()
    async with sm() as session:
        if wipe:
            await session.execute(delete(Customer))  # cascades to orders/items
            await session.commit()
            print("-wiped existing customers")

        batch: list[Customer] = []
        for i in range(n):
            batch.append(_make_customer(i, fake, now))
            if len(batch) >= 50:
                session.add_all(batch)
                await session.commit()
                batch.clear()
                print(f"-{i + 1}/{n} customers", flush=True)
        if batch:
            session.add_all(batch)
            await session.commit()

    print(f"[ok] seeded {n} customers with realistic orders")


def main() -> None:
    if sys.platform == "win32":
        # asyncpg + the Proactor loop emits noisy SSL-teardown tracebacks at interpreter exit
        # on Windows; the selector loop avoids it and is the recommended loop for asyncpg here.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    p = argparse.ArgumentParser(description="Seed Kairos with realistic shoppers + orders.")
    p.add_argument("--customers", type=int, default=2000)
    p.add_argument("--wipe", action="store_true", help="delete existing customers first")
    p.add_argument("--create-all", action="store_true", help="create tables before seeding")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducible demo data")
    args = p.parse_args()
    asyncio.run(seed(args.customers, args.wipe, args.create_all, args.seed))


if __name__ == "__main__":
    main()
