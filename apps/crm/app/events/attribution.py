"""Turn a conversion event into a real, campaign-attributed order.

The brief asks us to surface "an order came because of this communication." Rather than
booking a flat per-channel amount on the message, a ``converted`` callback now materializes a
real ``orders`` row linked back to its campaign and the exact message that drove it — with a
realistic order value the channel reports on the conversion. ``campaign_stats.revenue`` then
rolls up from real order rows, so the invariant ``SUM(orders.amount) == campaign_stats.revenue``
holds and ROAS is computed from orders, not a guess.

These two functions are the pure seam (no DB), unit-tested in ``tests/test_attribution.py``.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.events.economics import CHANNEL_AOV, money
from app.models.campaign import Message
from app.models.customer import Order


def conversion_amount(value: float | None, channel: str) -> Decimal:
    """The order value for a conversion.

    Prefer the value the channel reported on the conversion callback (realistic, varied). Fall
    back to the channel's average order value only if a callback omits it, so the rollup never
    silently books zero.
    """
    if value is not None:
        return money(value)
    return money(CHANNEL_AOV.get(channel, CHANNEL_AOV["email"]))


def build_attributed_order(msg: Message, amount: Decimal, occurred_at: datetime) -> Order:
    """Build the ``orders`` row credited to a message's conversion.

    ``external_id`` is derived from the message id: a message converts at most once (the state
    machine can't re-enter ``converted``), so this is stable and collision-free — and it makes
    the order idempotent if a conversion callback is ever replayed.
    """
    return Order(
        customer_id=msg.customer_id,
        external_id=f"conv-{msg.id}",
        amount=amount,
        currency="INR",
        status="placed",
        ordered_at=occurred_at,
        campaign_id=msg.campaign_id,
        attributed_message_id=msg.id,
        source="campaign",
    )
