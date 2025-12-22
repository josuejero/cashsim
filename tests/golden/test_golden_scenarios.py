from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path

import pandas as pd

from cashsim.batch import run_from_config
from cashsim.io.exporters import metrics_to_dict, normalize_series_for_export

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
START = date.fromisoformat("2025-01-01")
DAYS = 31


def _stable_series_csv(df: pd.DataFrame) -> str:
    out = normalize_series_for_export(df)
    buf = io.StringIO()
    out.to_csv(buf, index=False, lineterminator="\n", float_format="%.2f")
    return buf.getvalue()


def test_golden_scenarios_match_snapshot() -> None:
    assert GOLDEN_DIR.exists(), f"Golden dir missing: {GOLDEN_DIR} (run scripts/regen_golden.py)"

    scenario_dirs = sorted([p for p in GOLDEN_DIR.iterdir() if p.is_dir()])
    assert scenario_dirs, "No golden scenarios found (run scripts/regen_golden.py)"

    for scen in scenario_dirs:
        cfg = scen / "config.json"
        exp_metrics_path = scen / "metrics.json"
        exp_series_path = scen / "series.csv"

        assert cfg.exists(), f"Missing {cfg}"
        assert exp_metrics_path.exists(), f"Missing {exp_metrics_path}"
        assert exp_series_path.exists(), f"Missing {exp_series_path}"

        run = run_from_config(config=cfg, start=START, days=DAYS)

        expected_metrics = json.loads(exp_metrics_path.read_text(encoding="utf-8"))
        actual_metrics = metrics_to_dict(run.metrics)
        assert actual_metrics == expected_metrics, (
            f"Metrics mismatch for {scen.name}. "
            "If change is intentional: python scripts/regen_golden.py --overwrite"
        )

        expected_series = exp_series_path.read_text(encoding="utf-8")
        actual_series = _stable_series_csv(run.df)
        assert actual_series == expected_series, (
            f"Series mismatch for {scen.name}. "
            "If change is intentional: python scripts/regen_golden.py --overwrite"
        )


def test_basic_invariants_hold_for_golden_scenarios() -> None:
    scenario_dirs = sorted([p for p in GOLDEN_DIR.iterdir() if p.is_dir()])
    for scen in scenario_dirs:
        cfg = scen / "config.json"
        run = run_from_config(config=cfg, start=START, days=DAYS)

        df = run.df
        assert len(df) == DAYS
        assert "date" in df.columns

        # No NaNs in numeric columns
        num = df.select_dtypes(include=["number"])
        assert not num.isna().any().any(), f"NaNs found in numeric columns for {scen.name}"

        # Date monotonicity
        dates = pd.to_datetime(df["date"]).dt.date
        assert dates.is_monotonic_increasing

        # Required core columns should exist
        for col in ["balance", "earn", "bill_due", "gas_bucket"]:
            assert col in df.columns, f"Missing {col} for {scen.name}"
