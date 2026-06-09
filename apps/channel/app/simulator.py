"""Pure lifecycle simulation.

Given a channel and an RNG, produce the ordered list of lifecycle events a single message
will emit — with monotonic sequence numbers and (unscaled) delays. Keeping this pure makes
the whole ordering/funnel model deterministic and unit-testable.

The funnel is conditional: each stage only happens if the previous did. A message either
fails early or progresses sent → delivered → opened → read → clicked → converted, dropping
off at any stage.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Conditional probabilities P(stage | previous stage) per channel.
CHANNEL_FUNNEL: dict[str, dict[str, float]] = {
    "whatsapp": {"delivered": 0.92, "opened": 0.80, "read": 0.88, "clicked": 0.26, "converted": 0.22},
    "sms":      {"delivered": 0.88, "opened": 0.45, "read": 0.70, "clicked": 0.10, "converted": 0.12},
    "email":    {"delivered": 0.95, "opened": 0.38, "read": 0.75, "clicked": 0.14, "converted": 0.10},
    "rcs":      {"delivered": 0.90, "opened": 0.62, "read": 0.82, "clicked": 0.20, "converted": 0.18},
}
DEFAULT_FUNNEL = CHANNEL_FUNNEL["email"]

# (stage, (min_delay, max_delay)) added on top of the previous event's delay, in seconds.
_STAGES: list[tuple[str, tuple[float, float]]] = [
    ("delivered", (1, 8)),
    ("opened", (5, 120)),
    ("read", (2, 30)),
    ("clicked", (3, 90)),
    ("converted", (30, 600)),
]


@dataclass(frozen=True)
class PlannedEvent:
    event_type: str
    sequence: int
    delay: float  # seconds from send (unscaled)


def plan_lifecycle(channel: str, rng: random.Random, failure_rate: float) -> list[PlannedEvent]:
    funnel = CHANNEL_FUNNEL.get(channel, DEFAULT_FUNNEL)
    events: list[PlannedEvent] = []
    seq = 1
    t = rng.uniform(0.2, 2.0)
    events.append(PlannedEvent("sent", seq, t))
    seq += 1

    # Hard failure (invalid number / opt-out) instead of delivery.
    if rng.random() < failure_rate:
        t += rng.uniform(1, 5)
        events.append(PlannedEvent("failed", seq, t))
        return events

    for stage, (lo, hi) in _STAGES:
        if rng.random() < funnel[stage]:
            t += rng.uniform(lo, hi)
            events.append(PlannedEvent(stage, seq, t))
            seq += 1
        else:
            # A delivery miss surfaces as FAILED; later drop-offs are just silence.
            if stage == "delivered":
                t += rng.uniform(5, 30)
                events.append(PlannedEvent("failed", seq, t))
            break

    return events
