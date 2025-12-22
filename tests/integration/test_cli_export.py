from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cashsim.cli import app


def _write_config(tmp: Path) -> Path:
    cfg = {
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
    p = tmp / "cfg.json"
    p.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return p


def test_cli_export_writes_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "export",
            "--config",
            str(cfg),
            "--start",
            "2025-01-01",
            "--days",
            "10",
            "--out",
            str(out),
            "--series-format",
            "csv",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (out / "metrics.json").exists()
    assert (out / "series.csv").exists()
    assert (out / "run_meta.json").exists()


def test_cli_export_refuses_existing_output_without_overwrite(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"

    args = [
        "export",
        "--config",
        str(cfg),
        "--start",
        "2025-01-01",
        "--days",
        "10",
        "--out",
        str(out),
        "--series-format",
        "csv",
    ]

    result1 = runner.invoke(app, args)
    assert result1.exit_code == 0, result1.stdout

    result2 = runner.invoke(app, args)
    assert result2.exit_code != 0
    assert "Refusing to overwrite existing file:" in result2.output
    assert "Traceback" not in result2.output
