from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from cashsim.sim.types import SimMetrics

BASE_SERIES_COLUMNS: list[str] = [
    "date",
    "weekday",
    "earn",
    "bill_due",
    "balance",
    "gas_bucket",
    "fillups",
    "cc_events",
    "cc_interest_posted",
    "cc_min_paid",
    "cc_extra_on_due",
    "oneoff_contribs",
    "oneoff_paid",
    "total_cc_balance",
    "total_iou_balance",
    "accrued_interest_unposted",
]

EVENT_COLUMNS: list[str] = [
    "cc_events",
    "cc_interest_posted",
    "cc_min_paid",
    "cc_extra_on_due",
    "oneoff_contribs",
    "oneoff_paid",
]


def _json_default(obj: object) -> str:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


def metrics_to_dict(metrics: SimMetrics) -> dict[str, object]:
    d = asdict(metrics)
    out: dict[str, object] = {}
    for k, v in d.items():
        if isinstance(v, date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _normalize_series_for_export(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)

    for col in out.columns:
        if out[col].dtype == "object" and col in EVENT_COLUMNS:
            out[col] = out[col].apply(
                lambda v: json.dumps(
                    v or [],
                    separators=(",", ":"),
                    default=_json_default,
                )
            )

    cc_cols = sorted([c for c in out.columns if c.startswith("cc_") and c.endswith("_bal")])
    base = [c for c in BASE_SERIES_COLUMNS if c in out.columns]
    remaining = sorted([c for c in out.columns if c not in set(base + cc_cols)])

    ordered = base + cc_cols + remaining
    return out[ordered]


def write_metrics_json(metrics: SimMetrics, path: Path) -> None:
    path.write_text(
        json.dumps(metrics_to_dict(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_series_csv(df: pd.DataFrame, path: Path) -> None:
    out = _normalize_series_for_export(df)
    out.to_csv(path, index=False, lineterminator="\n", float_format="%.2f")


def write_series_json(df: pd.DataFrame, path: Path) -> None:
    out = _normalize_series_for_export(df)
    records = out.to_dict(orient="records")
    path.write_text(json.dumps(records, indent=2, default=_json_default) + "\n", encoding="utf-8")


def write_events_csv(df: pd.DataFrame, path: Path) -> None:
    rows: list[dict[str, object]] = []

    if "date" not in df.columns:
        raise ValueError("series df missing 'date' column")

    for _, r in df.iterrows():
        day = r["date"]
        for col in EVENT_COLUMNS:
            if col not in df.columns:
                continue
            events = r[col] or []
            for ev in events:
                if isinstance(ev, dict):
                    row = {"date": day, "kind": col}
                    row.update(ev)
                    rows.append(row)
                else:
                    rows.append({"date": day, "kind": col, "raw": ev})

    out = pd.DataFrame.from_records(rows)
    if len(out) == 0:
        out = pd.DataFrame(columns=["date", "kind"])

    out.to_csv(path, index=False, lineterminator="\n")


def prepare_outdir(out_dir: Path, *, overwrite: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    if not overwrite:
        for name in [
            "metrics.json",
            "series.csv",
            "series.json",
            "events.csv",
            "compare.json",
            "series_diff.csv",
            "run_meta.json",
        ]:
            p = out_dir / name
            if p.exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {p} (use --overwrite)")


def write_run(
    *,
    out_dir: Path,
    df: pd.DataFrame,
    metrics: SimMetrics,
    config_path: Path,
    start: str,
    days: int,
    series_format: str,
    include_events: bool,
    overwrite: bool,
) -> None:
    prepare_outdir(out_dir, overwrite=overwrite)

    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "config_path": str(config_path),
                "start": start,
                "days": days,
                "series_format": series_format,
                "include_events": include_events,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    write_metrics_json(metrics, out_dir / "metrics.json")

    fmt = series_format.lower()
    if fmt == "csv":
        write_series_csv(df, out_dir / "series.csv")
    elif fmt == "json":
        write_series_json(df, out_dir / "series.json")
    else:
        raise ValueError("series_format must be 'csv' or 'json'")

    if include_events:
        write_events_csv(df, out_dir / "events.csv")


def normalize_series_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Public wrapper for the project’s stable series normalization.

    API and CLI must share the same formatting rules so clients can rely on exported columns.
    """
    return _normalize_series_for_export(df)
