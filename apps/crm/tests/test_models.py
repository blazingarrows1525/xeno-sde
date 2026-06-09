"""Model tests that need no database — they prove the schema and ORM mappers are valid."""
from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401  (register all mappers)
from app.models.base import Base

EXPECTED_TABLES = {
    "customers",
    "orders",
    "order_items",
    "segments",
    "segment_members",
    "campaigns",
    "messages",
    "communication_events",
    "campaign_stats",
    "agent_runs",
    "agent_steps",
    "ai_recommendations",
}


def test_all_mappers_configure():
    # Raises if any relationship / back_populates is misconfigured.
    configure_mappers()


def test_expected_tables_exist():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_event_log_has_idempotency_constraint():
    t = Base.metadata.tables["communication_events"]
    assert "uq_event_idempotency" in {c.name for c in t.constraints}


def test_message_idempotency_key_is_unique():
    t = Base.metadata.tables["messages"]
    assert t.c.idempotency_key.unique is True


def test_customer_has_performance_indexes():
    t = Base.metadata.tables["customers"]
    index_names = {ix.name for ix in t.indexes}
    assert "ix_customers_last_order_at" in index_names
    assert "ix_customers_ltv" in index_names
