"""A conversion callback must carry a realistic order value; no other event may.

This pins the channel half of the attribution contract — the CRM books a real order from the
value the channel reports on `converted`.
"""
from random import Random

from app.simulator import CHANNEL_AOV, plan_lifecycle


def _first_converted_plan(channel: str):
    """Return the first seed (out of many) whose lifecycle actually reaches `converted`."""
    for s in range(2000):
        plan = plan_lifecycle(channel, Random(s), failure_rate=0.0)
        if any(e.event_type == "converted" for e in plan):
            return plan
    raise AssertionError(f"no converted lifecycle found for {channel}")


def test_only_the_conversion_event_carries_a_value():
    plan = _first_converted_plan("whatsapp")
    for e in plan:
        if e.event_type == "converted":
            assert e.value is not None and e.value > 0
        else:
            assert e.value is None


def test_conversion_value_is_in_the_channel_band():
    plan = _first_converted_plan("email")
    conv = next(e for e in plan if e.event_type == "converted")
    base = CHANNEL_AOV["email"]
    assert 0.25 * base <= conv.value <= 4.0 * base


def test_non_converting_lifecycle_has_no_value():
    # A guaranteed failure never converts, so nothing carries a value.
    plan = plan_lifecycle("sms", Random(0), failure_rate=1.0)
    assert all(e.value is None for e in plan)
