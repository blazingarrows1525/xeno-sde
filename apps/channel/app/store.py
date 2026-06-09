"""In-memory provider-message registry with idempotent send dedup.

In-memory is deliberate for this scope; at volume this becomes a Redis/KV store keyed by
idempotency_key. The contract is the important part: the same idempotency_key always maps to
the same provider_message_id and is simulated exactly once.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from app.schemas import SendItem


@dataclass
class ProviderMessage:
    provider_message_id: str
    message_id: str
    channel: str
    recipient: str
    idempotency_key: str
    campaign_id: str | None = None
    customer_id: str | None = None
    state: str = "accepted"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d


class ChannelStore:
    def __init__(self) -> None:
        self._by_idem: dict[str, ProviderMessage] = {}
        self._by_pid: dict[str, ProviderMessage] = {}

    def register(self, item: SendItem) -> tuple[ProviderMessage, bool]:
        """Return (record, created). Deduplicates on idempotency_key."""
        existing = self._by_idem.get(item.idempotency_key)
        if existing is not None:
            return existing, False

        pid = "pm_" + uuid.uuid4().hex[:16]
        record = ProviderMessage(
            provider_message_id=pid,
            message_id=item.message_id,
            channel=item.channel,
            recipient=item.recipient,
            idempotency_key=item.idempotency_key,
            campaign_id=item.campaign_id,
            customer_id=item.customer_id,
        )
        self._by_idem[item.idempotency_key] = record
        self._by_pid[pid] = record
        return record, True

    def get(self, provider_message_id: str) -> ProviderMessage | None:
        return self._by_pid.get(provider_message_id)
