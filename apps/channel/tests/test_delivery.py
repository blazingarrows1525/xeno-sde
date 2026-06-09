"""Callback reliability: retry on 5xx, dead-letter on exhaustion, no retry on 4xx."""
import httpx

from app import delivery


async def _noop(*args, **kwargs):
    pass


async def test_retry_on_5xx_then_success(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _noop)
    delivery.DEAD_LETTERS.clear()
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ok = await delivery.post_callback(client, "http://crm/receipts", {"events": []}, "s", 3)

    assert ok is True
    assert calls["n"] == 2
    assert delivery.DEAD_LETTERS == []


async def test_persistent_5xx_dead_letters(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _noop)
    delivery.DEAD_LETTERS.clear()

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        ok = await delivery.post_callback(client, "http://crm/receipts", {"events": []}, "s", 2)

    assert ok is False
    assert len(delivery.DEAD_LETTERS) == 1
    assert delivery.DEAD_LETTERS[0]["reason"] == "max_retries"


async def test_4xx_is_not_retried(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _noop)
    delivery.DEAD_LETTERS.clear()
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(422)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ok = await delivery.post_callback(client, "http://crm/receipts", {"events": []}, "s", 5)

    assert ok is False
    assert calls["n"] == 1  # 4xx is permanent — no retries
    assert delivery.DEAD_LETTERS[0]["reason"] == "http_422"


async def test_network_error_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", _noop)
    delivery.DEAD_LETTERS.clear()
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ok = await delivery.post_callback(client, "http://crm/receipts", {"events": []}, "s", 3)

    assert ok is True
    assert calls["n"] == 2
