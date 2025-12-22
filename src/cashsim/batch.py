from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from cashsim.io.config_io import load_config
from cashsim.sim.core import simulate_month
from cashsim.sim.types import SimMetrics


@dataclass(frozen=True)
class RunResult:
    config_path: Path
    start: date
    days: int
    df: pd.DataFrame
    metrics: SimMetrics


def run_from_config(*, config: Path, start: date, days: int) -> RunResult:
    dials = load_config(config)
    df, metrics = simulate_month(dials, start=start, days=days)
    return RunResult(
        config_path=Path(config).resolve(),
        start=start,
        days=days,
        df=df,
        metrics=metrics,
    )
