"""HMAC-SHA256 signing for callbacks so the CRM can authenticate receipts."""
from __future__ import annotations

import hashlib
import hmac


def sign(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify(secret: str, body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign(secret, body), signature or "")
