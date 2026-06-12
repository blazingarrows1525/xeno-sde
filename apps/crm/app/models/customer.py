"""Customers and their orders — the data we ingest and segment on."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    external_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    first_name: Mapped[str | None]
    email: Mapped[str | None] = mapped_column(String, index=True)
    phone_e164: Mapped[str | None]
    whatsapp_opt_in: Mapped[bool] = mapped_column(server_default=text("false"))
    email_opt_in: Mapped[bool] = mapped_column(server_default=text("false"))
    city: Mapped[str | None] = mapped_column(String, index=True)

    # Denormalized rollups (refreshed on order ingest / nightly) so segmentation stays fast.
    total_spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    total_orders: Mapped[int] = mapped_column(server_default=text("0"))
    ltv: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

    __table_args__ = (
        Index("ix_customers_last_order_at", "last_order_at"),
        Index("ix_customers_ltv", "ltv"),
        Index("ix_customers_whatsapp_opt_in", "whatsapp_opt_in"),
    )


class Order(UUIDPKMixin, Base):
    __tablename__ = "orders"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'INR'"))
    status: Mapped[str] = mapped_column(String, server_default=text("'placed'"))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Campaign attribution — set when this order is credited to a communication
    # ("an order came because of this campaign"). NULL for organic orders. The denormalized
    # customer rollups (total_spend/ltv) refresh on a schedule, so an attributed order row is
    # the source of truth for campaign revenue and ROAS.
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), index=True
    )
    attributed_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String, server_default=text("'organic'"))

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_orders_customer_ordered", "customer_id", "ordered_at"),)


class OrderItem(UUIDPKMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str]
    product_name: Mapped[str]
    qty: Mapped[int] = mapped_column(server_default=text("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship(back_populates="items")
