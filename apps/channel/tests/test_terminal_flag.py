"""The CRM settles a campaign when every message hits its terminal event, so the channel
must mark exactly one event per lifecycle ``terminal`` — the last one."""
import json

import httpx

from app import delivery
from app.simulator import PlannedEvent
from app.store import ProviderMessage


async def _noop(*args, **kwargs):
    pass


async def test_only_the_last_event_is_terminal(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _noop)
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200)

    record = ProviderMessage(
        provider_message_id="pm_x",
        message_id="m1",
        channel="whatsapp",
        recipient="+9198",
        idempotency_key="k1",
    )
    plan = [
        PlannedEvent("sent", 1, 0.1),
        PlannedEvent("delivered", 2, 0.2),
        PlannedEvent("opened", 3, 0.3),
    ]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await delivery.run_lifecycle(
            record, plan, client=client, url="http://crm/v1/receipts",
            secret="s", time_scale=0.0, max_retries=1,
        )

    terminal_flags = [b["events"][0]["terminal"] for b in bodies]
    assert terminal_flags == [False, False, True]  # exactly one, and it's the last
    assert [b["events"][0]["event_type"] for b in bodies] == ["sent", "delivered", "opened"]
