"""Customer + order ingestion endpoints (the Xeno "data ingestion" requirement)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.customer import Customer, Order, OrderItem

router = APIRouter(tags=["customers"])


# ── schemas ──────────────────────────────────────────────────────────────

class CustomerIn(BaseModel):
    external_id: str
    first_name: str | None = None
    email: str | None = None
    phone_e164: str | None = None
    whatsapp_opt_in: bool = False
    email_opt_in: bool = False
    city: str | None = None
    total_spend: Decimal = Decimal("0")
    total_orders: int = 0
    ltv: Decimal = Decimal("0")
    last_order_at: datetime | None = None


class OrderItemIn(BaseModel):
    sku: str
    product_name: str
    qty: int = 1
    unit_price: Decimal


class OrderIn(BaseModel):
    customer_external_id: str
    external_id: str
    amount: Decimal
    currency: str = "INR"
    status: str = "placed"
    ordered_at: datetime
    items: list[OrderItemIn] = []


class BulkResult(BaseModel):
    created: int
    updated: int
    errors: int


# ── routes ───────────────────────────────────────────────────────────────

@router.post("/customers:bulk", response_model=BulkResult)
async def bulk_upsert_customers(
    customers: list[CustomerIn], session: AsyncSession = Depends(get_session)
) -> BulkResult:
    """Upsert customers by external_id.  Idempotent — safe to call repeatedly."""
    created = updated = errors = 0
    for c in customers:
        row = (
            await session.execute(
                select(Customer).where(Customer.external_id == c.external_id)
            )
        ).scalar_one_or_none()
        if row is None:
            session.add(Customer(**c.model_dump()))
            created += 1
        else:
            for k, v in c.model_dump(exclude_unset=True).items():
                if k != "external_id":
                    setattr(row, k, v)
            updated += 1
    await session.commit()
    return BulkResult(created=created, updated=updated, errors=errors)


@router.post("/orders:bulk", response_model=BulkResult)
async def bulk_create_orders(
    orders: list[OrderIn], session: AsyncSession = Depends(get_session)
) -> BulkResult:
    """Ingest orders, auto-updating customer rollups.  Idempotent on external_id."""
    created = updated = errors = 0
    for o in orders:
        exists = (
            await session.execute(
                select(Order.id).where(Order.external_id == o.external_id)
            )
        ).scalar_one_or_none()
        if exists:
            updated += 1
            continue

        cust = (
            await session.execute(
                select(Customer).where(Customer.external_id == o.customer_external_id)
            )
        ).scalar_one_or_none()
        if cust is None:
            errors += 1
            continue

        items = [
            OrderItem(sku=i.sku, product_name=i.product_name, qty=i.qty, unit_price=i.unit_price)
            for i in o.items
        ]
        order = Order(
            customer_id=cust.id,
            external_id=o.external_id,
            amount=o.amount,
            currency=o.currency,
            status=o.status,
            ordered_at=o.ordered_at,
            items=items,
        )
        session.add(order)

        # Update denormalized rollups
        cust.total_orders += 1
        cust.total_spend += o.amount
        cust.ltv += o.amount
        if cust.last_order_at is None or o.ordered_at > cust.last_order_at:
            cust.last_order_at = o.ordered_at
        created += 1

    await session.commit()
    return BulkResult(created=created, updated=updated, errors=errors)


@router.get("/customers/stats")
async def customer_stats(session: AsyncSession = Depends(get_session)) -> dict:
    """Quick summary for dashboards."""
    from sqlalchemy import func, text as sa_text

    total = await session.scalar(select(func.count(Customer.id)))
    wa = await session.scalar(
        select(func.count(Customer.id)).where(Customer.whatsapp_opt_in.is_(True))
    )
    avg_ltv = await session.scalar(select(func.round(func.avg(Customer.ltv), 2)))
    return {
        "total_customers": total or 0,
        "whatsapp_opt_in": wa or 0,
        "avg_ltv": float(avg_ltv) if avg_ltv else 0,
    }
