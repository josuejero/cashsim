from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import pandas as pd

from cashsim.models import Dials
from cashsim.sim.core import simulate_month


@dataclass
class BreakEvenRow:
    weekday_earnings: float
    min_balance: float
    label: str
    days_to_cashout: int | None


def _label_from(min_balance: float, cushion: float) -> str:
    if min_balance >= cushion:
        return "Safe"
    if min_balance >= 0:
        return "Okay"
    return "Risky"


def break_even_grid(dials: Dials, candidates: Iterable[float], *, days: int = 31) -> pd.DataFrame:
    rows: list[BreakEvenRow] = []
    for e in candidates:
        test = dials.model_copy(update={"weekday_earnings": float(e)})
        _df, m = simulate_month(test, days=days)
        days_to_cashout = (
            None if m.first_negative_date is None else (m.first_negative_date - date.today()).days
        )
        rows.append(
            BreakEvenRow(
                weekday_earnings=round(float(e), 2),
                min_balance=m.min_balance,
                label=_label_from(m.min_balance, test.safety_cushion),
                days_to_cashout=days_to_cashout,
            )
        )
    return pd.DataFrame([r.__dict__ for r in rows]).sort_values("weekday_earnings")
