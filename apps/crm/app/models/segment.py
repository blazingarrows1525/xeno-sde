"""Segments (a saved DSL) and their materialized membership snapshots."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Segment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "segments"

    name: Mapped[str]
    dsl: Mapped[dict] = mapped_column(JSONB)  # the typed Segment DSL document
    compiled_sql: Mapped[str | None]  # audit copy of the WHERE clause
    estimated_size: Mapped[int | None]
    status: Mapped[str] = mapped_column(String, server_default=text("'draft'"))

    members: Mapped[list["SegmentMember"]] = relationship(
        back_populates="segment", cascade="all, delete-orphan"
    )


class SegmentMember(Base):
    """A frozen snapshot of which customers were in a segment at a given version.

    A campaign targets a specific snapshot so its audience is reproducible even as the
    underlying shopper data keeps changing.
    """

    __tablename__ = "segment_members"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("segments.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    snapshot_version: Mapped[int] = mapped_column(primary_key=True, server_default=text("1"))
    materialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    segment: Mapped["Segment"] = relationship(back_populates="members")

    __table_args__ = (Index("ix_segment_members_seg_ver", "segment_id", "snapshot_version"),)
