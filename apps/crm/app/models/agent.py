"""Agent runs, their step-by-step trace (the glass box), and AI recommendations."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class AgentRun(UUIDPKMixin, Base):
    __tablename__ = "agent_runs"

    goal_text: Mapped[str]
    status: Mapped[str] = mapped_column(String, server_default=text("'running'"))
    tokens_in: Mapped[int] = mapped_column(server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), server_default=text("0"))
    outcome_summary: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["AiRecommendation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentStep(UUIDPKMixin, Base):
    """One entry in the reasoning trace streamed to the UI."""

    __tablename__ = "agent_steps"

    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE")
    )
    step_no: Mapped[int]
    step_type: Mapped[str]  # thought | tool_call | tool_result | message
    tool_name: Mapped[str | None]
    tool_input: Mapped[dict | None] = mapped_column(JSONB)
    tool_output: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    run: Mapped["AgentRun"] = relationship(back_populates="steps")

    __table_args__ = (Index("ix_agent_steps_run_step", "agent_run_id", "step_no"),)


class AiRecommendation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "ai_recommendations"

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE")
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL")
    )
    kind: Mapped[str]  # segment | channel | message | strategy
    content: Mapped[dict] = mapped_column(JSONB)
    predicted_kpis: Mapped[dict | None] = mapped_column(JSONB)
    rationale: Mapped[str | None]
    decision: Mapped[str | None]  # accepted | rejected | edited

    run: Mapped["AgentRun | None"] = relationship(back_populates="recommendations")
