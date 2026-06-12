"""The CRM→Channel send body must match the channel's SendItem contract, field for field."""
import uuid

from app.events.dispatch import to_send_payload
from app.models.campaign import Message

# Required by apps/channel/app/schemas.py::SendItem.
_REQUIRED = {"message_id", "channel", "recipient", "body", "idempotency_key"}


def _message() -> Message:
    cid, custid = uuid.uuid4(), uuid.uuid4()
    m = Message(
        campaign_id=cid,
        customer_id=custid,
        variant="A",
        channel="whatsapp",
        recipient="+9198765",
        rendered_body="Hi Aisha, a little something for you…",
        current_state="queued",
        last_sequence=0,
        idempotency_key=f"{cid}:{custid}",
    )
    m.id = uuid.uuid4()  # stand in for the post-flush PK the channel echoes back
    return m


def test_payload_carries_callback_and_required_fields():
    m = _message()
    payload = to_send_payload([m], "https://crm.example/v1/receipts")

    assert payload["callback_url"] == "https://crm.example/v1/receipts"
    item = payload["messages"][0]
    assert _REQUIRED <= item.keys()
    assert item["message_id"] == str(m.id)  # the id the channel will echo on every callback
    assert item["recipient"] == "+9198765"
    assert item["idempotency_key"] == f"{m.campaign_id}:{m.customer_id}"


def test_empty_audience_yields_no_messages():
    payload = to_send_payload([], "https://crm.example/v1/receipts")
    assert payload["messages"] == []
