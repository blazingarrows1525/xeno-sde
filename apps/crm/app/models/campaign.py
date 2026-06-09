"""Campaigns, the per-recipient messages they send, and the event log + stats rollup.

`communication_events` is the append-only source of truth; `campaign_stats` is a derived
rollup. The unique constraint on (message_id, event_type, sequence) makes at-least-once
callback delivery effectively-once.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Campaign(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("segments.id", ondelete="SET NULL")
    )
    name: Mapped[str]
    goal_text: Mapped[str | None]  # the original natural-language goal
    plan: Mapped[dict | None] = mapped_column(JSONB)  # channel, variants, schedule
    predicted_kpis: Mapped[dict | None] = mapped_column(JSONB)
    channel: Mapped[str]
    status: Mapped[str] = mapped_column(String, server_default=text("'draft'"), index=True)

    # The human approval gate: launch is refused while approved_by is NULL.
    approved_by: Mapped[str | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["Message"]] = relationship(back_populates="campaign")
    stats: Mapped["CampaignStats | None"] = relationship(
        back_populates="campaign", uselist=False, cascade="all, delete-orphan"
    )


class Message(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    variant: Mapped[str] = mapped_column(String, server_default=text("'A'"))
    channel: Mapped[str]
    recipient: Mapped[str]
    rendered_body: Mapped[str]

    current_state: Mapped[str] = mapped_column(String, server_default=text("'queued'"))
    last_sequence: Mapped[int] = mapped_column(server_default=text("0"))
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    provider_message_id: Mapped[str | None] = mapped_column(String, index=True)
    attributed_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))

    campaign: Mapped["Campaign"] = relationship(back_populates="messages")
    events: Mapped[list["CommunicationEvent"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_messages_campaign_state", "campaign_id", "current_state"),)


class CommunicationEvent(UUIDPKMixin, Base):
    __tablename__ = "communication_events"

    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE")
    )
    event_type: Mapped[str]  # sent|delivered|failed|opened|read|clicked|converted
    sequence: Mapped[int]  # monotonic per message; orders the lifecycle
    payload: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # channel clock
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # crm clock

    message: Mapped["Message"] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("message_id", "event_type", "sequence", name="uq_event_idempotency"),
        Index("ix_events_message_seq", "message_id", "sequence"),
    )


class CampaignStats(Base):
    """Incrementally-maintained rollup of the event log for fast dashboard reads."""

    __tablename__ = "campaign_stats"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    sent: Mapped[int] = mapped_column(server_default=text("0"))
    delivered: Mapped[int] = mapped_column(server_default=text("0"))
    failed: Mapped[int] = mapped_column(server_default=text("0"))
    opened: Mapped[int] = mapped_column(server_default=text("0"))
    read: Mapped[int] = mapped_column(server_default=text("0"))
    clicked: Mapped[int] = mapped_column(server_default=text("0"))
    converted: Mapped[int] = mapped_column(server_default=text("0"))
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    send_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="stats")
