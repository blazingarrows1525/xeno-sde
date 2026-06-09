"""Event-ordering state machine — how the CRM decides whether a receipt advances a message.

Channel callbacks are *at-least-once* and can arrive *out of order*. Two mechanisms keep the
denormalized `messages.current_state` correct:

1. **Idempotency** is enforced at the DB layer by `unique(message_id, event_type, sequence)`,
   so the event log counts each distinct event exactly once (that drives the stats rollup).
2. **Ordering** is enforced here: `current_state` only advances on an event whose `sequence`
   is greater than the last applied one *and* whose transition is legal. A late/duplicate
   (lower-or-equal sequence) event is recorded in the log but never regresses the state.

`decide()` is a pure function so the whole contract is unit-testable without a database.
"""
from __future__ import annotations

from dataclasses import dataclass

EVENT_TO_STATE: dict[str, str] = {
    "sent": "sent",
    "delivered": "delivered",
    "opened": "opened",
    "read": "read",
    "clicked": "clicked",
    "converted": "converted",
    "failed": "failed",
}

STATE_RANK: dict[str, int] = {
    "queued": 0,
    "sent": 1,
    "delivered": 2,
    "opened": 3,
    "read": 4,
    "clicked": 5,
    "converted": 6,
    "failed": 99,  # terminal
}

TERMINAL_STATES = {"failed"}
FAILABLE_FROM = {"queued", "sent", "delivered"}  # a FAILED only makes sense pre-engagement


@dataclass(frozen=True)
class ApplyDecision:
    action: str  # "advance" | "stale" | "illegal"
    new_state: str | None = None
    new_sequence: int | None = None


def decide(
    current_state: str, last_sequence: int, event_type: str, sequence: int
) -> ApplyDecision:
    """Decide how an incoming event affects a message's denormalized state.

    - ``advance``  : apply it; move to ``new_state`` / ``new_sequence``.
    - ``stale``    : older-or-equal sequence (duplicate or out-of-order) — record, don't regress.
    - ``illegal``  : unknown event or an impossible transition — record, don't apply.
    """
    if event_type not in EVENT_TO_STATE:
        return ApplyDecision("illegal")
    if sequence <= last_sequence:
        return ApplyDecision("stale")
    if current_state in TERMINAL_STATES:
        return ApplyDecision("illegal")

    if event_type == "failed":
        if current_state in FAILABLE_FROM:
            return ApplyDecision("advance", "failed", sequence)
        return ApplyDecision("illegal")

    target = EVENT_TO_STATE[event_type]
    if STATE_RANK[target] > STATE_RANK[current_state]:
        return ApplyDecision("advance", target, sequence)
    return ApplyDecision("illegal")
