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


def test_export_csv_has_series_csv_field() -> None:
    payload = {
        "dials": _dials_dict(),
        "start": "2025-01-01",
        "days": 10,
        "series_format": "csv",
        "include_events": False,
    }
    r = client.post("/v1/export", json=payload)
    assert r.status_code == 200, r.text

    body = r.json()
    assert "metrics" in body
    assert "meta" in body
    assert body.get("series_csv")
    assert body.get("series_json") is None


def test_export_json_has_series_json_field() -> None:
    payload = {
        "dials": _dials_dict(),
        "start": "2025-01-01",
        "days": 10,
        "series_format": "json",
        "include_events": False,
    }
    r = client.post("/v1/export", json=payload)
    assert r.status_code == 200, r.text

    body = r.json()
    assert isinstance(body.get("series_json"), list)
    assert body.get("series_csv") is None
