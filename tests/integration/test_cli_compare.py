from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cashsim.cli import app


def test_cli_compare_writes_compare_json(tmp_path: Path) -> None:
    runner = CliRunner()

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"

    base = {
        "current_cash": 300.0,
        "safety_cushion": 150.0,
        "weekday_earnings": 120.0,
        "gas_pct": 0.15,
        "gas_fill_size": 25.0,
        "bills": [{"name": "Rent", "usual_day": 1, "amount": 500.0}],
        "credit_cards": [],
        "ious": [],
        "oneoffs": [],
        "invest": {
            "enable": False,
            "hysa_apy": 0.045,
            "expected_market_return": 0.07,
            "use_dca": False,
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
    }

    base2 = dict(base)
    base2["weekday_earnings"] = 140.0

    a.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
    b.write_text(json.dumps(base2, indent=2) + "\n", encoding="utf-8")

    out = tmp_path / "cmp"

    args = [
        "compare",
        "--a",
        str(a),
        "--b",
        str(b),
        "--start",
        "2025-01-01",
        "--days",
        "10",
        "--out",
        str(out),
    ]

    res = runner.invoke(app, args)

    assert res.exit_code == 0, res.stdout
    assert (out / "compare.json").exists()
