"""Async delivery: walk a planned lifecycle and POST signed callbacks with retries + DLQ.

Reliability model:
- 2xx            -> success, stop.
- 4xx            -> permanent failure, dead-letter (retrying won't help).
- 5xx / network  -> transient, retry with exponential backoff + jitter, then dead-letter.
"""
from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime, timezone

import httpx

from app.core.signing import sign
from app.simulator import PlannedEvent
from app.store import ProviderMessage

# Visible for the /v1/admin/dead-letters debug endpoint and tests.
DEAD_LETTERS: list[dict] = []


def backoff_delay(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Exponential backoff with full jitter."""
    return min(cap, base * (2**attempt)) * (0.5 + random.random())


async def post_callback(
    client: httpx.AsyncClient, url: str, payload: dict, secret: str, max_retries: int
) -> bool:
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"X-Signature": sign(secret, body), "Content-Type": "application/json"}

    for attempt in range(max_retries + 1):
        response = None
        try:
            response = await client.post(url, content=body, headers=headers)
        except httpx.HTTPError:
            response = None  # transient network error -> retry

        if response is not None:
            if 200 <= response.status_code < 300:
                return True
            if 400 <= response.status_code < 500:
                DEAD_LETTERS.append({"reason": f"http_{response.status_code}", "payload": payload})
                return False
            # 5xx falls through to retry

        if attempt < max_retries:
            await asyncio.sleep(backoff_delay(attempt))

    DEAD_LETTERS.append({"reason": "max_retries", "payload": payload})
    return False


async def run_lifecycle(
    record: ProviderMessage,
    plan: list[PlannedEvent],
    *,
    client: httpx.AsyncClient,
    url: str,
    secret: str,
    time_scale: float,
    max_retries: int,
) -> None:
    previous = 0.0
    for event in plan:
        await asyncio.sleep(max(0.0, event.delay - previous) * time_scale)
        previous = event.delay
        record.state = event.event_type
        payload = {
            "events": [
                {
                    "provider_message_id": record.provider_message_id,
                    "message_id": record.message_id,
                    "event_type": event.event_type,
                    "sequence": event.sequence,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        await post_callback(client, url, payload, secret, max_retries)
