from __future__ import annotations

from fastapi.testclient import TestClient

from cashsim.api.app import app

client = TestClient(app)


def _dials_dict() -> dict:
    return {
        "current_cash": 300.0,
        "safety_cushion": 150.0,
        "weekday_earnings": 120.0,
        "gas_pct": 0.10,
        "gas_fill_size": 25.0,
        "bills": [{"name": "rent", "amount": 200.0, "usual_day": 5}],
        "oneoffs": [],
        "credit_cards": [],
        "ious": [],
        "interest_mode": "statement_adb",
    }


def test_simulate_valid_payload_200_and_schema_stable() -> None:
    payload = {"dials": _dials_dict(), "start": "2025-01-01", "days": 10}
    r = client.post("/v1/simulate", json=payload)
    assert r.status_code == 200, r.text

    body = r.json()
    assert set(body.keys()) == {"metrics", "series"}
    assert "min_balance" in body["metrics"]
    assert isinstance(body["series"], list)
    assert len(body["series"]) == 10


def test_simulate_invalid_payload_422() -> None:
    r = client.post("/v1/simulate", json={"start": "2025-01-01", "days": 10})
    assert r.status_code == 422
