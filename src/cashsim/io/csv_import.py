from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pydantic import BaseModel, Field

from cashsim.io.config_io import load_config
from cashsim.models import IOU, Bill, CreditCard, Dials, OneOff


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_bool(x: object) -> bool | None:
    if pd.isna(cast(Any, x)):
        return None
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in {"true", "t", "1", "yes", "y"}:
        return True
    if s in {"false", "f", "0", "no", "n", ""}:
        return False
    raise ValueError(f"Invalid boolean: {x!r}")


class BillRow(BaseModel):
    name: str = Field(min_length=1)
    amount: float = Field(gt=0)
    usual_day: int = Field(ge=1, le=31)
    priority: int = Field(ge=0, le=1000, default=100)
    must_pay: bool = True


class CardRow(BaseModel):
    name: str = Field(min_length=1)
    balance: float = Field(ge=0)
    apr: float = Field(ge=0, le=1, default=0.0)
    due_day: int | None = Field(default=None)
    min_pct: float = Field(ge=0, le=1, default=0.02)
    min_floor: float = Field(ge=0, default=25.0)


class OneOffRow(BaseModel):
    name: str = Field(min_length=1)
    due_date: date
    amount: float = Field(gt=0)
    priority: int = Field(ge=0, le=1000, default=50)
    must_pay: bool = False


def _read_csv_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _validate_rows[T: BaseModel](df: pd.DataFrame, model: type[T], *, strict: bool) -> list[T]:
    if df.empty:
        return []

    df = df.replace({"": None})

    for col in ("must_pay",):
        if col in df.columns:
            df[col] = df[col].map(_coerce_bool)

    expected = set(model.model_fields.keys())
    got = set(df.columns)
    if strict:
        extra = sorted(got - expected)
        if extra:
            raise ValueError(f"Unexpected columns: {extra}")

    rows: list[T] = []
    for rec in df.to_dict(orient="records"):
        cleaned = {k: v for k, v in rec.items() if k in expected and not pd.isna(v)}
        rows.append(model.model_validate(cleaned))
    return rows


def import_input_tables(
    in_dir: Path,
    *,
    base_config: Path | None = None,
    strict: bool = False,
) -> Dials:
    """Import canonical input tables into a Dials object.

    Rules:
    - If dials.json exists in in_dir, it is used as the base.
    - Else, base_config must be provided.
    - Any table CSV present overrides the corresponding list in the base.
    """

    in_dir = in_dir.resolve()
    dials_json = in_dir / "dials.json"

    if dials_json.exists():
        base = _read_json(dials_json)
    elif base_config is not None:
        base = load_config(base_config).model_dump(mode="json")
    else:
        raise FileNotFoundError(
            "Missing dials.json in input folder and no --base-config provided. "
            "Run export-inputs first or pass --base-config."
        )

    bills_df = _read_csv_df(in_dir / "bills.csv")
    cards_df = _read_csv_df(in_dir / "credit_cards.csv")
    ious_df = _read_csv_df(in_dir / "ious.csv")
    oneoffs_df = _read_csv_df(in_dir / "oneoffs.csv")

    if "due_day" in bills_df.columns and "usual_day" not in bills_df.columns:
        bills_df = bills_df.rename(columns={"due_day": "usual_day"})

    bills_rows = _validate_rows(bills_df, BillRow, strict=strict)
    cards_rows = _validate_rows(cards_df, CardRow, strict=strict)
    ious_rows = _validate_rows(ious_df, CardRow, strict=strict)
    oneoffs_rows = _validate_rows(oneoffs_df, OneOffRow, strict=strict)

    if not bills_df.empty:
        base["bills"] = [Bill(**r.model_dump()) for r in bills_rows]
    if not cards_df.empty:
        base["credit_cards"] = [CreditCard(**r.model_dump()) for r in cards_rows]
    if not ious_df.empty:
        base["ious"] = [IOU(**r.model_dump()) for r in ious_rows]
    if not oneoffs_df.empty:
        base["oneoffs"] = [OneOff(**r.model_dump()) for r in oneoffs_rows]

    if (in_dir / "bills.csv").exists() and bills_df.empty:
        base["bills"] = []
    if (in_dir / "credit_cards.csv").exists() and cards_df.empty:
        base["credit_cards"] = []
    if (in_dir / "ious.csv").exists() and ious_df.empty:
        base["ious"] = []
    if (in_dir / "oneoffs.csv").exists() and oneoffs_df.empty:
        base["oneoffs"] = []

    return Dials.model_validate(base)
