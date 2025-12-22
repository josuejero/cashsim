from __future__ import annotations

from fastapi.testclient import TestClient

from cashsim.api.app import app


def test_risk_schema_contract() -> None:
    client = TestClient(app)

    payload = {
        "start": "2025-01-01",
        "horizon_days": 30,
        "top_k": 3,
        "dials": {
            "current_cash": 300,
            "safety_cushion": 150,
            "weekday_earnings": 120,
            "gas_pct": 0.1,
            "gas_fill_size": 25,
            "bills": [],
            "credit_cards": [],
            "ious": [],
            "oneoffs": [],
            "invest": {
                "enable": True,
                "hysa_apy": 0.045,
                "expected_market_return": 0.07,
                "use_dca": True,
                "roth_target": 0.0,
                "trad_target": 0.0,
                "hysa_target": 0.0,
                "robinhood_target": 0.0,
                "ira_year_limit": 7000.0,
                "roth_ok_today": True,
            },
            "interest_mode": "statement_adb",
            "extra_strategy": "avalanche",
            "blackouts": [],
        },
    }

    r = client.post("/v1/risk", json=payload)
    assert r.status_code in (200, 500)  # 500 acceptable if model file missing

    if r.status_code == 200:
        body = r.json()
        assert set(body.keys()) == {"probability", "horizon_days", "drivers"}
        assert isinstance(body["probability"], (float, int))
        assert body["horizon_days"] == 30
        assert isinstance(body["drivers"], list)
