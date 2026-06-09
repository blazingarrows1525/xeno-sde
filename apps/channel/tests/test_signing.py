"""HMAC signing round-trip."""
from app.core.signing import sign, verify


def test_sign_verify_roundtrip():
    body = b'{"a":1}'
    sig = sign("secret", body)
    assert sig.startswith("sha256=")
    assert verify("secret", body, sig) is True


def test_verify_rejects_tampered_body_or_wrong_secret():
    body = b'{"a":1}'
    sig = sign("secret", body)
    assert verify("secret", b'{"a":2}', sig) is False
    assert verify("wrong-secret", body, sig) is False
    assert verify("secret", body, "sha256=deadbeef") is False
