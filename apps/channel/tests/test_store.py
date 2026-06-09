"""Idempotent send registry."""
from app.schemas import SendItem
from app.store import ChannelStore


def _item(key: str, mid: str = "m1") -> SendItem:
    return SendItem(
        message_id=mid, channel="whatsapp", recipient="+9198", body="hi", idempotency_key=key
    )


def test_register_dedups_on_idempotency_key():
    store = ChannelStore()
    r1, created1 = store.register(_item("k1"))
    r2, created2 = store.register(_item("k1"))
    assert created1 is True
    assert created2 is False
    assert r1.provider_message_id == r2.provider_message_id


def test_distinct_keys_get_distinct_providers():
    store = ChannelStore()
    r1, _ = store.register(_item("k1"))
    r2, _ = store.register(_item("k2"))
    assert r1.provider_message_id != r2.provider_message_id


def test_get_returns_record_or_none():
    store = ChannelStore()
    r, _ = store.register(_item("k1"))
    assert store.get(r.provider_message_id) is r
    assert store.get("missing") is None
