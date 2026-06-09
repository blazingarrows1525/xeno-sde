"""The simulator is the deterministic, ordered core of the channel — heavily invariant-tested."""
import random

from app.simulator import plan_lifecycle

_ORDER = {"sent": 0, "delivered": 1, "opened": 2, "read": 3, "clicked": 4, "converted": 5, "failed": 99}


def _check_invariants(plan):
    assert plan, "plan is never empty"
    assert plan[0].event_type == "sent"
    seqs = [e.sequence for e in plan]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)  # strictly increasing, unique
    delays = [e.delay for e in plan]
    assert delays == sorted(delays)  # non-decreasing in time
    types = [e.event_type for e in plan]
    if "failed" in types or "converted" in types:
        assert plan[-1].event_type in ("failed", "converted")  # terminal ends the plan
    non_failed = [t for t in types if t != "failed"]
    ranks = [_ORDER[t] for t in non_failed]
    assert ranks == sorted(ranks)  # funnel order respected


def test_failure_rate_one_yields_only_sent_then_failed():
    plan = plan_lifecycle("whatsapp", random.Random(1), failure_rate=1.0)
    assert [e.event_type for e in plan] == ["sent", "failed"]
    assert [e.sequence for e in plan] == [1, 2]


def test_invariants_hold_across_many_seeds():
    for s in range(300):
        _check_invariants(plan_lifecycle("whatsapp", random.Random(s), failure_rate=0.0))
        _check_invariants(plan_lifecycle("sms", random.Random(s), failure_rate=0.05))


def test_unknown_channel_falls_back_to_default_funnel():
    plan = plan_lifecycle("carrier-pigeon", random.Random(0), failure_rate=0.0)
    assert plan[0].event_type == "sent"
