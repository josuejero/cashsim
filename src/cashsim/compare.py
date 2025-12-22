from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

import pandas as pd

from cashsim.sim.types import SimMetrics


def _date_to_str(v: date | None) -> str | None:
    return v.isoformat() if isinstance(v, date) else None


def metrics_delta(a: SimMetrics, b: SimMetrics) -> dict[str, Any]:
    da = asdict(a)
    db = asdict(b)

    out: dict[str, Any] = {
        "a": {k: (_date_to_str(v) if isinstance(v, date) else v) for k, v in da.items()},
        "b": {k: (_date_to_str(v) if isinstance(v, date) else v) for k, v in db.items()},
        "delta": {},
    }

    for k in da:
        va = da[k]
        vb = db[k]
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            out["delta"][k] = round(vb - va, 2)
        else:
            # For non-numeric fields (dates), surface both; deeper logic comes in later phases.
            out["delta"][k] = {
                "a": _date_to_str(va) if isinstance(va, date) else va,
                "b": _date_to_str(vb) if isinstance(vb, date) else vb,
            }

    return out


def series_diff(df_a: pd.DataFrame, df_b: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    a = df_a.copy()
    b = df_b.copy()

    a["date"] = pd.to_datetime(a["date"]).dt.date
    b["date"] = pd.to_datetime(b["date"]).dt.date

    a = a[["date"] + [c for c in columns if c in a.columns]].set_index("date")
    b = b[["date"] + [c for c in columns if c in b.columns]].set_index("date")

    joined = a.join(b, how="outer", lsuffix="_a", rsuffix="_b").reset_index()

    for c in columns:
        ca = f"{c}_a"
        cb = f"{c}_b"
        if ca in joined.columns and cb in joined.columns:
            joined[f"{c}_delta"] = (joined[cb] - joined[ca]).round(2)

    joined["date"] = joined["date"].astype(str)
    return joined
