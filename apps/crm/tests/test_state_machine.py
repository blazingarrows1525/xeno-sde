"""The event-ordering contract: monotonic advance, stale-on-reorder, illegal transitions."""
from app.events import decide


def test_happy_path_advances_through_the_funnel():
    state, seq = "queued", 0
    for event_type, s in [
        ("sent", 1), ("delivered", 2), ("opened", 3),
        ("read", 4), ("clicked", 5), ("converted", 6),
    ]:
        d = decide(state, seq, event_type, s)
        assert d.action == "advance"
        state, seq = d.new_state, d.new_sequence
    assert state == "converted" and seq == 6


def test_duplicate_sequence_is_stale():
    assert decide("delivered", 2, "delivered", 2).action == "stale"


def test_late_lower_sequence_does_not_regress():
    # Already at opened (seq 3); a delivered (seq 2) arrives late.
    d = decide("opened", 3, "delivered", 2)
    assert d.action == "stale"
    assert d.new_state is None


def test_higher_sequence_may_skip_an_intermediate_state():
    # opened (seq 3) arrives while still 'sent' (last seq 1).
    d = decide("sent", 1, "opened", 3)
    assert d.action == "advance"
    assert d.new_state == "opened" and d.new_sequence == 3


def test_unknown_event_type_is_illegal():
    assert decide("sent", 1, "exploded", 2).action == "illegal"


def test_failed_before_engagement_advances():
    assert decide("delivered", 2, "failed", 3).action == "advance"


def test_failed_after_engagement_is_illegal():
    assert decide("clicked", 5, "failed", 6).action == "illegal"


def test_nothing_applies_after_terminal_failed():
    assert decide("failed", 2, "delivered", 3).action == "illegal"


def test_cannot_regress_after_converted():
    assert decide("converted", 6, "sent", 7).action == "illegal"
