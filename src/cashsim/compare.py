from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import date
from typing import Any

import pandas as pd

from cashsim.sim.types import SimMetrics

TIMELINE_FIELDS: list[str] = [
    "min_balance_date",
    "first_negative_date",
    "friend_ask_latest_date",
    "cushion_breach_date",
]

SERIES_DEFAULT_COLUMNS: list[str] = [
    "balance",
    "total_cc_balance",
    "total_iou_balance",
    "accrued_interest_unposted",
    "earn",
    "bill_due",
    "gas_bucket",
]


def _date_to_str(v: date | None) -> str | None:
    return v.isoformat() if isinstance(v, date) else None


def metrics_delta(a: SimMetrics, b: SimMetrics) -> dict[str, Any]:
    """Stable summary delta for top-level metrics.

    Numeric fields become numbers in `delta`.
    Non-numeric fields (dates) remain {a,b} records.

    This format is intentionally simple for:
    - JSON diff review
    - downstream automation that reads numeric deltas
    """

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
        if isinstance(va, int | float) and isinstance(vb, int | float):
            out["delta"][k] = round(vb - va, 2)
        else:
            out["delta"][k] = {
                "a": _date_to_str(va) if isinstance(va, date) else va,
                "b": _date_to_str(vb) if isinstance(vb, date) else vb,
            }

    return out


def series_diff(df_a: pd.DataFrame, df_b: pd.DataFrame, *, columns: list[str]) -> pd.DataFrame:
    """Aligned day-by-day delta table for selected numeric columns.

    Output columns are suffixed with _a, _b, and _delta.
    The join is outer to make missing dates visible.
    """

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


def timeline_deltas(
    a: SimMetrics, b: SimMetrics, *, fields: list[str] = TIMELINE_FIELDS
) -> dict[str, Any]:
    """Key date deltas with delta_days when both sides are present."""

    out: dict[str, Any] = {}
    for f in fields:
        da = getattr(a, f, None)
        db = getattr(b, f, None)

        delta_days: int | None = None
        if isinstance(da, date) and isinstance(db, date):
            delta_days = (db - da).days

        out[f] = {
            "a": _date_to_str(da) if isinstance(da, date) else None,
            "b": _date_to_str(db) if isinstance(db, date) else None,
            "delta_days": delta_days,
        }

    return out


def _sum_event_amounts(cell: Iterable[object] | None) -> float:
    """Sum amounts from a per-day event cell.

    The engine uses tuple-like events (name, amount) today.
    This helper also tolerates dict events that include amt/amount.

    Returning 0.0 for empty/None helps stability in aggregates.
    """

    if not cell:
        return 0.0

    total = 0.0
    for ev in cell:
        if isinstance(ev, dict):
            if "amt" in ev:
                total += float(ev["amt"])
            elif "amount" in ev:
                total += float(ev["amount"])
        elif isinstance(ev, list | tuple) and len(ev) >= 2:
            try:
                total += float(ev[1])
            except (TypeError, ValueError):
                continue

    return round(total, 2)


def category_totals(df: pd.DataFrame) -> dict[str, float]:
    """Coarse aggregates for human-readable comparisons.

    These are intentionally “big buckets” so reviewers can quickly infer meaning.
    They are not meant to replace detailed series inspection.
    """

    out: dict[str, float] = {}

    out["income"] = round(float(df["earn"].sum()), 2) if "earn" in df.columns else 0.0
    out["non_debt_bills"] = (
        round(float(df["bill_due"].sum()), 2) if "bill_due" in df.columns else 0.0
    )

    if "cc_min_paid" in df.columns:
        out["cc_mins_paid"] = round(float(df["cc_min_paid"].apply(_sum_event_amounts).sum()), 2)
    else:
        out["cc_mins_paid"] = 0.0

    if "cc_extra_on_due" in df.columns:
        out["cc_extra_paid"] = round(
            float(df["cc_extra_on_due"].apply(_sum_event_amounts).sum()), 2
        )
    else:
        out["cc_extra_paid"] = 0.0

    if "oneoff_paid" in df.columns:
        out["oneoffs_paid"] = round(float(df["oneoff_paid"].apply(_sum_event_amounts).sum()), 2)
    else:
        out["oneoffs_paid"] = 0.0

    if "cc_interest_posted" in df.columns:
        out["interest_posted"] = round(
            float(df["cc_interest_posted"].apply(_sum_event_amounts).sum()), 2
        )
    else:
        out["interest_posted"] = 0.0

    out["debt_payments_total"] = round(out["cc_mins_paid"] + out["cc_extra_paid"], 2)
    out["spend_total"] = round(out["non_debt_bills"] + out["oneoffs_paid"], 2)

    return out


def category_deltas(df_a: pd.DataFrame, df_b: pd.DataFrame) -> dict[str, Any]:
    a = category_totals(df_a)
    b = category_totals(df_b)

    keys = sorted(set(a) | set(b))
    out: dict[str, Any] = {}
    for k in keys:
        va = float(a.get(k, 0.0))
        vb = float(b.get(k, 0.0))
        out[k] = {"a": round(va, 2), "b": round(vb, 2), "delta": round(vb - va, 2)}
    return out


def series_summary(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    *,
    columns: list[str],
    threshold: float = 0.01,
) -> dict[str, Any]:
    """Summarize divergence for selected series columns.

    This provides a “where should I look first?” hint for reviewers.
    - max_abs_delta + date: fastest spot check
    - RMSE: overall drift
    - threshold exceed: first date a meaningful diff appears
    """

    diff = series_diff(df_a, df_b, columns=columns)

    out: dict[str, Any] = {}
    for c in columns:
        dcol = f"{c}_delta"
        if dcol not in diff.columns:
            continue

        ser = pd.to_numeric(diff[dcol], errors="coerce")
        abs_ser = ser.abs()

        if abs_ser.notna().any():
            idx = int(abs_ser.idxmax())
            max_abs = float(abs_ser.max())
            max_date = str(diff.loc[idx, "date"])
            rmse = float((ser.dropna() ** 2).mean() ** 0.5) if ser.dropna().size else 0.0
            mean_abs = float(abs_ser.dropna().mean()) if abs_ser.dropna().size else 0.0
        else:
            max_abs = 0.0
            max_date = None
            rmse = 0.0
            mean_abs = 0.0

        exceed = abs_ser > threshold
        first_exceed = str(diff.loc[exceed, "date"].iloc[0]) if exceed.any() else None

        out[c] = {
            "threshold": threshold,
            "max_abs_delta": round(max_abs, 2),
            "max_abs_delta_date": max_date,
            "rmse": round(rmse, 2),
            "mean_abs_delta": round(mean_abs, 2),
            "days_exceeding_threshold": int(exceed.sum()),
            "first_exceeds_threshold_date": first_exceed,
        }

    return out


def build_compare_payload(
    *,
    metrics_a: SimMetrics,
    metrics_b: SimMetrics,
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    start: str,
    days: int,
    series_columns: list[str] | None = None,
    threshold: float = 0.01,
) -> dict[str, Any]:
    cols = series_columns or SERIES_DEFAULT_COLUMNS

    return {
        "metrics": metrics_delta(metrics_a, metrics_b),
        "timeline": timeline_deltas(metrics_a, metrics_b),
        "category_totals": category_deltas(df_a, df_b),
        "series_summary": series_summary(df_a, df_b, columns=cols, threshold=threshold),
        "meta": {
            "start": start,
            "days": days,
            "series_columns": cols,
            "threshold": threshold,
        },
    }


def render_compare_markdown(payload: dict[str, Any], *, series_diff_path: str | None = None) -> str:
    """Deterministic, human-readable Markdown report."""

    lines: list[str] = []
    lines.append("# CashSim Compare Report")

    meta = payload.get("meta", {})
    lines.append("")
    lines.append(f"- start: {meta.get('start')}")
    lines.append(f"- days: {meta.get('days')}")
    lines.append(f"- threshold: {meta.get('threshold')}")
    if series_diff_path:
        lines.append(f"- series_diff: {series_diff_path}")

    metrics = payload.get("metrics", {})
    a = metrics.get("a", {})
    b = metrics.get("b", {})
    d = metrics.get("delta", {})

    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append("| metric | A | B | delta |")
    lines.append("|---|---:|---:|---:|")

    keys = sorted(a.keys())
    for k in keys:
        va = a.get(k)
        vb = b.get(k)
        dv = d.get(k)
        if isinstance(dv, dict):
            lines.append(f"| {k} | {va} | {vb} |  |")
        else:
            lines.append(f"| {k} | {va} | {vb} | {dv} |")

    timeline = payload.get("timeline", {})
    lines.append("")
    lines.append("## Timeline deltas")
    lines.append("")
    lines.append("| field | A | B | delta_days |")
    lines.append("|---|---|---|---:|")
    for k in sorted(timeline.keys()):
        t = timeline[k]
        lines.append(f"| {k} | {t.get('a')} | {t.get('b')} | {t.get('delta_days')} |")

    cats = payload.get("category_totals", {})
    lines.append("")
    lines.append("## Category totals")
    lines.append("")
    lines.append("| category | A | B | delta |")
    lines.append("|---|---:|---:|---:|")
    for k in sorted(cats.keys()):
        c = cats[k]
        lines.append(f"| {k} | {c.get('a')} | {c.get('b')} | {c.get('delta')} |")

    ss = payload.get("series_summary", {})
    lines.append("")
    lines.append("## Series divergence summary")
    lines.append("")
    lines.append(
        "| column | max_abs_delta | date | rmse | days_exceeding_threshold | "
        "first_exceeds_threshold_date |"
    )
    lines.append("|---|---:|---|---:|---:|---|")
    for k in sorted(ss.keys()):
        s = ss[k]
        lines.append(
            (
                "| {col} | {max_abs_delta} | {date} | {rmse} | {days_exceeding} | {first_exceeds} |"
            ).format(
                col=k,
                max_abs_delta=s.get("max_abs_delta"),
                date=s.get("max_abs_delta_date"),
                rmse=s.get("rmse"),
                days_exceeding=s.get("days_exceeding_threshold"),
                first_exceeds=s.get("first_exceeds_threshold_date"),
            )
        )

    lines.append("")
    return "\n".join(lines)
