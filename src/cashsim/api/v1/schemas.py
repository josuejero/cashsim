from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from cashsim.models import Dials


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dials: Dials
    start: date = Field(..., description="Start date (YYYY-MM-DD)")
    days: int = Field(31, ge=1, le=366)


class SimMetricsWire(BaseModel):
    """Wire-safe metrics (date fields are ISO strings or null)."""

    model_config = ConfigDict(extra="forbid")

    min_balance: float
    min_balance_date: str | None
    first_negative_date: str | None
    total_upcoming_bills: float
    friend_ask_needed: float
    friend_ask_latest_date: str | None
    cushion_breach_date: str | None
    accrued_interest_estimate: float


class SimulateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: SimMetricsWire
    series: list[dict[str, Any]]


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    a: Dials
    b: Dials
    start: date
    days: int = Field(31, ge=1, le=366)
    series: bool = False
    threshold: float = Field(0.01, ge=0)


class CompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: dict[str, Any]
    timeline: dict[str, Any]
    category_totals: dict[str, Any]
    series_summary: dict[str, Any]
    meta: dict[str, Any]
    series_diff: list[dict[str, Any]] | None = None


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dials: Dials
    start: date
    days: int = Field(31, ge=1, le=366)
    series_format: Literal["csv", "json"] = "csv"
    include_events: bool = False


class ExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: SimMetricsWire
    meta: dict[str, Any]

    # Exactly one of these should be present based on series_format:
    series_csv: str | None = None
    series_json: list[dict[str, Any]] | None = None

    # Present only if include_events=true
    events_csv: str | None = None
