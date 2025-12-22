from __future__ import annotations

import logging
import time
from io import StringIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from opentelemetry import trace

from cashsim.compare import build_compare_payload, series_diff
from cashsim.io.exporters import EVENT_COLUMNS, metrics_to_dict, normalize_series_for_export
from cashsim.sim.core import simulate_month

from .schemas import (
    CompareRequest,
    CompareResponse,
    ExportRequest,
    ExportResponse,
    RiskDriverOut,
    RiskRequest,
    RiskResponse,
    SimMetricsWire,
    SimulateRequest,
    SimulateResponse,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("cashsim.api")
router = APIRouter()


def _records_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    records = df.to_dict(orient="records")
    return [{str(k): v for k, v in record.items()} for record in records]


def _series_records_raw(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Match CLI `cashsim simulate`: engine raw series records."""
    return _records_from_df(df)


def _series_records_export(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Match CLI `cashsim export --series-format json`: normalized, stable records."""
    out = normalize_series_for_export(df)
    return _records_from_df(out)


def _series_csv_export(df: pd.DataFrame) -> str:
    """Match CLI `cashsim export --series-format csv`: normalized, stable CSV."""
    out = normalize_series_for_export(df)
    buf = StringIO()

    # lineterminator avoids Windows-style CRLF surprises in tests
    out.to_csv(buf, index=False, lineterminator="\n", float_format="%.2f")
    return buf.getvalue()


def _events_csv_export(df: pd.DataFrame) -> str:
    """Flatten per-day nested event lists into a single CSV string."""

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

    # Stable date serialization
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)

    buf = StringIO()
    out.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue()


@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    t0 = time.perf_counter()
    logger.info(
        "simulate_start",
        extra={
            "event": "simulate_start",
            "days": req.days,
            "start_date": str(req.start),
            "current_cash": float(req.dials.current_cash),
            "weekday_earnings": float(req.dials.weekday_earnings),
        },
    )

    try:
        with tracer.start_as_current_span("cashsim.simulate") as span:
            span.set_attribute("cashsim.days", req.days)
            span.set_attribute("cashsim.start_date", str(req.start))

            df, metrics = simulate_month(req.dials, start=req.start, days=req.days)

            span.set_attribute("cashsim.rows", int(len(df)))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    dt_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "simulate_end",
        extra={
            "event": "simulate_end",
            "duration_ms": round(dt_ms, 2),
            "rows": int(len(df)),
        },
    )

    return SimulateResponse(
        metrics=SimMetricsWire.model_validate(metrics_to_dict(metrics)),
        series=_series_records_raw(df),
    )


@router.post("/risk", response_model=RiskResponse)
def risk(req: RiskRequest) -> RiskResponse:
    try:
        from cashsim.risk import predict_overdraft_risk
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Risk dependencies are not installed. Install with: pip install 'cashsim[ml]'",
        ) from exc

    try:
        result = predict_overdraft_risk(
            req.dials,
            start=req.start,
            horizon_days=req.horizon_days,
            top_k=req.top_k,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RiskResponse(
        probability=result.probability,
        horizon_days=result.horizon_days,
        drivers=[
            RiskDriverOut(
                feature=d.feature,
                contribution=d.contribution,
                direction=d.direction,
                value=d.value,
            )
            for d in result.drivers
        ],
    )


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    try:
        df_a, m_a = simulate_month(req.a, start=req.start, days=req.days)
        df_b, m_b = simulate_month(req.b, start=req.start, days=req.days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    payload = build_compare_payload(
        metrics_a=m_a,
        metrics_b=m_b,
        df_a=df_a,
        df_b=df_b,
        start=req.start.isoformat(),
        days=req.days,
        threshold=req.threshold,
    )

    # API keeps series_diff optional
    if req.series:
        cols = payload.get("meta", {}).get("series_columns", [])
        diff = series_diff(df_a, df_b, columns=list(cols))
        payload["series_diff"] = _records_from_df(diff)
    else:
        payload["series_diff"] = None

    return CompareResponse(**payload)


@router.post("/export", response_model=ExportResponse)
def export(req: ExportRequest) -> ExportResponse:
    try:
        df, metrics = simulate_month(req.dials, start=req.start, days=req.days)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    metrics_wire = SimMetricsWire.model_validate(metrics_to_dict(metrics))
    meta = {
        "start": req.start.isoformat(),
        "days": req.days,
        "series_format": req.series_format,
        "include_events": req.include_events,
    }

    payload: dict[str, Any] = {"metrics": metrics_wire, "meta": meta}

    if req.series_format == "csv":
        payload["series_csv"] = _series_csv_export(df)
    else:
        payload["series_json"] = _series_records_export(df)

    if req.include_events:
        payload["events_csv"] = _events_csv_export(df)

    return ExportResponse(**payload)
