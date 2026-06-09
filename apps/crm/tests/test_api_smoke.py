"""Smoke tests for the FastAPI app — proves the API layer wires up without a database."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_preview_compiles_valid_dsl():
    r = client.post(
        "/v1/segments/preview",
        json={"dsl": {"rules": [{"field": "days_since_last_order", "op": "gte", "value": 60}]}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["params"] == {"p0": 60}
    assert "EXTRACT(EPOCH" in body["compiled_where"]


def test_preview_rejects_invalid_dsl_with_422():
    r = client.post(
        "/v1/segments/preview",
        json={"dsl": {"rules": [{"field": "evil", "op": "eq", "value": 1}]}},
    )
    assert r.status_code == 422
