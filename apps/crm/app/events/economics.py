"""Per-channel unit economics, shared by the live receipt rollup and the offline sim.

Keeping these in one place means a campaign settled by real Channel-Service callbacks and
one settled by the in-process fallback compute revenue and cost the same way — so the
Insights numbers stay consistent regardless of which path ran.
"""
from __future__ import annotations

import random
from decimal import Decimal

CHANNEL_COST = {"whatsapp": 0.85, "sms": 0.30, "email": 0.10, "rcs": 0.50}  # INR / message
CHANNEL_AOV = {"whatsapp": 2800, "sms": 1900, "email": 3000, "rcs": 2600}   # INR / conversion


def money(x: float) -> Decimal:
    """Round a float to a 2dp Decimal for the Numeric(12, 2) money columns."""
    return Decimal(str(round(x, 2)))


def value_spread(base: float, rng: random.Random) -> Decimal:
    """A realistic, right-skewed order value around ``base``.

    Real order values aren't a flat constant — most cluster near the average with a long tail
    of larger baskets. A lognormal (median 1.0, σ=0.45) reproduces that shape; we clamp the
    multiplier to [0.25, 4.0] so a draw can't produce a silly value.
    """
    factor = min(4.0, max(0.25, rng.lognormvariate(0.0, 0.45)))
    return money(base * factor)


def draw_order_value(channel: str, rng: random.Random) -> Decimal:
    """Draw a single conversion's order value for ``channel`` (used by the offline paths)."""
    return value_spread(CHANNEL_AOV.get(channel, CHANNEL_AOV["email"]), rng)
