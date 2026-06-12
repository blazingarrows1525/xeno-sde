"""Per-channel unit economics, shared by the live receipt rollup and the offline sim.

Keeping these in one place means a campaign settled by real Channel-Service callbacks and
one settled by the in-process fallback compute revenue and cost the same way — so the
Insights numbers stay consistent regardless of which path ran.
"""
from __future__ import annotations

from decimal import Decimal

CHANNEL_COST = {"whatsapp": 0.85, "sms": 0.30, "email": 0.10, "rcs": 0.50}  # INR / message
CHANNEL_AOV = {"whatsapp": 2800, "sms": 1900, "email": 3000, "rcs": 2600}   # INR / conversion


def money(x: float) -> Decimal:
    """Round a float to a 2dp Decimal for the Numeric(12, 2) money columns."""
    return Decimal(str(round(x, 2)))
