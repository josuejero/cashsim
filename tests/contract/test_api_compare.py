from __future__ import annotations

from fastapi.testclient import TestClient

from cashsim.api.app import app

client = TestClient(app)


def _base() -> dict:
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


def test_compare_metrics_delta_deterministic() -> None:
    a = _base()
    b = {**_base(), "weekday_earnings": 130.0}

    payload = {"a": a, "b": b, "start": "2025-01-01", "days": 10, "series": False}
    r1 = client.post("/v1/compare", json=payload)
    r2 = client.post("/v1/compare", json=payload)

    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    assert r1.json() == r2.json()
