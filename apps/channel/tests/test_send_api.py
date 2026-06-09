"""Send API: idempotent acceptance + the failure-rate demo knob (no background delivery)."""
from app.core.config import settings

settings.auto_deliver = False  # don't spawn delivery tasks during tests

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _payload(key="c1:m1", mid="m1"):
    return {
        "messages": [
            {
                "message_id": mid,
                "channel": "whatsapp",
                "recipient": "+9198",
                "body": "hi",
                "idempotency_key": key,
            }
        ],
        "callback_url": "http://crm/receipts",
    }


def test_send_accepts_then_dedups_same_idempotency_key():
    r = client.post("/v1/send", json=_payload())
    assert r.status_code == 202
    body = r.json()
    assert body["accepted"] == 1 and body["duplicates"] == 0
    pid = body["provider_messages"][0]["provider_message_id"]

    again = client.post("/v1/send", json=_payload()).json()
    assert again["accepted"] == 0 and again["duplicates"] == 1
    assert again["provider_messages"][0]["provider_message_id"] == pid


def test_failure_rate_is_validated():
    assert client.post("/v1/admin/failure-rate", json={"rate": 0.5}).status_code == 200
    assert client.post("/v1/admin/failure-rate", json={"rate": 2}).status_code == 422


def test_health():
    assert client.get("/health").json()["status"] == "ok"
