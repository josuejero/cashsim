from __future__ import annotations

from pathlib import Path

import pandas as pd

from cashsim.ml.synth import generate


def test_risk_pipeline_smoke(tmp_path: Path) -> None:
    df = generate(n=200, seed=123, start=pd.Timestamp("2025-01-01").date(), horizon_days=30)
    assert "label_overdraft" in df.columns
    assert len(df) == 200
