"""The conversion-attribution seam: a `converted` event becomes a real, campaign-attributed
order, and conversion values are varied (not a flat per-channel constant).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from random import Random

from app.events.attribution import build_attributed_order, conversion_amount
from app.events.economics import CHANNEL_AOV, draw_order_value, money, value_spread
from app.models.campaign import Message


# ── conversion_amount ──────────────────────────────────────────────────────

def test_conversion_amount_prefers_the_reported_value():
    assert conversion_amount(2999.5, "email") == Decimal("2999.50")


def test_conversion_amount_falls_back_to_channel_aov():
    assert conversion_amount(None, "whatsapp") == money(CHANNEL_AOV["whatsapp"])


def test_conversion_amount_unknown_channel_uses_email_aov():
    assert conversion_amount(None, "carrier-pigeon") == money(CHANNEL_AOV["email"])


# ── build_attributed_order ─────────────────────────────────────────────────

def _msg() -> Message:
    m = Message(
        campaign_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        channel="whatsapp",
        recipient="+910000000000",
        rendered_body="hi",
        idempotency_key="k",
    )
    m.id = uuid.uuid4()
    return m


def test_build_attributed_order_links_campaign_message_and_customer():
    msg = _msg()
    when = datetime.now(timezone.utc)
    order = build_attributed_order(msg, Decimal("1234.50"), when)

    assert order.source == "campaign"
    assert order.campaign_id == msg.campaign_id
    assert order.attributed_message_id == msg.id
    assert order.customer_id == msg.customer_id
    assert order.amount == Decimal("1234.50")
    assert order.ordered_at == when
    # Derived from the message id → stable + collision-free → idempotent on replay.
    assert order.external_id == f"conv-{msg.id}"


# ── value spread (no more flat AOV) ────────────────────────────────────────

def test_value_spread_is_varied_not_constant():
    rng = Random(7)
    draws = [float(value_spread(3000, rng)) for _ in range(200)]
    assert len(set(draws)) > 50  # genuinely varied, not a single constant


def test_value_spread_is_clamped_to_a_sane_band():
    rng = Random(11)
    base = 3000
    draws = [float(value_spread(base, rng)) for _ in range(500)]
    assert all(0.25 * base <= d <= 4.0 * base for d in draws)


def test_value_spread_median_sits_near_base():
    rng = Random(5)
    base = 3000
    draws = sorted(float(value_spread(base, rng)) for _ in range(400))
    median = draws[len(draws) // 2]
    assert 0.5 * base <= median <= 2.0 * base  # lognormal median = base


def test_value_spread_is_deterministic_for_a_seed():
    assert value_spread(1000, Random(1)) == value_spread(1000, Random(1))


def test_draw_order_value_uses_the_channel_band():
    rng = Random(3)
    base = CHANNEL_AOV["sms"]
    draws = [float(draw_order_value("sms", rng)) for _ in range(100)]
    assert all(0.25 * base <= d <= 4.0 * base for d in draws)
