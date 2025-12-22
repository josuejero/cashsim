from __future__ import annotations

import filecmp
import json
from pathlib import Path

from typer.testing import CliRunner

from cashsim.cli import app


def test_cli_export_is_deterministic(tmp_path: Path) -> None:
    runner = CliRunner()

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    args = [
        "export",
        "--config",
        str(cfg),
        "--start",
        "2025-01-01",
        "--days",
        "10",
        "--series-format",
        "csv",
    ]

    r1 = runner.invoke(app, args + ["--out", str(out1)])
    assert r1.exit_code == 0, r1.stdout

    r2 = runner.invoke(app, args + ["--out", str(out2)])
    assert r2.exit_code == 0, r2.stdout

    assert filecmp.cmp(out1 / "metrics.json", out2 / "metrics.json", shallow=False)
    assert filecmp.cmp(out1 / "series.csv", out2 / "series.csv", shallow=False)
