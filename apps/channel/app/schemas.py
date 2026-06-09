"""Request schemas for the Channel Service send API."""
from __future__ import annotations

from pydantic import BaseModel


class SendItem(BaseModel):
    message_id: str
    campaign_id: str | None = None
    customer_id: str | None = None
    channel: str
    recipient: str
    body: str
    idempotency_key: str


class SendRequest(BaseModel):
    messages: list[SendItem]
    callback_url: str | None = None  # defaults to settings.crm_receipts_url
