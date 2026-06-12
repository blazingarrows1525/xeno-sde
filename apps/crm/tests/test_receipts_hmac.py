"""The receipt endpoint must accept the signature the Channel Service actually sends.

The channel signs callbacks as ``X-Signature: sha256=<hex>`` (apps/channel/app/core/signing.py).
These tests pin that the CRM verifier accepts that exact form — the bug that would otherwise
make every real callback 401 and silently break the live loop.
"""
import hashlib
import hmac

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.receipts import _verify_hmac
from app.core.config import settings
from app.main import app

client = TestClient(app)


def _channel_signature(body: bytes) -> str:
    digest = hmac.new(settings.receipt_hmac_secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"  # exactly what apps/channel signing.sign() emits


def test_accepts_channel_prefixed_signature():
    body = b'{"events":[{"message_id":"m1"}]}'
    _verify_hmac(body, _channel_signature(body))  # must not raise


def test_accepts_bare_hex_signature():
    body = b'{"events":[]}'
    bare = _channel_signature(body).split("=", 1)[1]
    _verify_hmac(body, bare)  # must not raise


def test_rejects_tampered_body():
    signed = b'{"events":[]}'
    tampered = b'{"events":[{"injected":true}]}'
    with pytest.raises(HTTPException):
        _verify_hmac(tampered, _channel_signature(signed))


def test_rejects_missing_signature():
    with pytest.raises(HTTPException):
        _verify_hmac(b"{}", None)


# ── endpoint level (no DB: the HMAC guard runs before any query) ───────────

def test_endpoint_rejects_unsigned_callback():
    r = client.post("/v1/receipts", json={"events": []})
    assert r.status_code == 401


def test_endpoint_rejects_bad_signature():
    r = client.post("/v1/receipts", json={"events": []}, headers={"X-Signature": "sha256=deadbeef"})
    assert r.status_code == 401
