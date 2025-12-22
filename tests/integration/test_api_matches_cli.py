from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from cashsim.api.app import app as api_app
from cashsim.cli import app as cli_app

client = TestClient(api_app)


def _write_config(tmp: Path) -> Path:
    cfg = {
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
    path = tmp / "cfg.json"
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def test_api_simulate_matches_cli_simulate(tmp_path: Path) -> None:
    cfg_path = _write_config(tmp_path)
    start = "2025-01-01"
    days = "10"

    # CLI
    runner = CliRunner()
    r = runner.invoke(
        cli_app, ["simulate", "--config", str(cfg_path), "--start", start, "--days", days]
    )
    assert r.exit_code == 0, r.stdout
    cli_body = json.loads(r.stdout)

    # API
    dials = json.loads(cfg_path.read_text(encoding="utf-8"))
    api_body = client.post(
        "/v1/simulate", json={"dials": dials, "start": start, "days": int(days)}
    ).json()

    assert api_body["metrics"] == cli_body["metrics"]
    assert api_body["series"] == cli_body["series"]
