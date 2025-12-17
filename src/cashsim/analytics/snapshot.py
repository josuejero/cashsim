from __future__ import annotations

from datetime import date
from typing import Any, TypedDict

import pandas as pd

from cashsim.models import Dials


class Snapshot(TypedDict):
    events: list[dict[str, Any]]
    first_date: date | None
    last_date: date | None
    income: float
    gas: float
    leftover: float


def monthly_snapshot(dials: Dials, months: int = 1) -> Snapshot:
    months = max(1, min(6, int(months)))
    today = date.today()
    result: Snapshot = {
        "events": [],
        "first_date": None,
        "last_date": None,
        "income": 0.0,
        "gas": 0.0,
        "leftover": 0.0,
    }

    for k in range(months):
        first_ts = (pd.Timestamp(today).to_period("M") + k).to_timestamp()
        last_ts = (pd.Timestamp(today).to_period("M") + k + 1).to_timestamp()

        workday_count = 20
        income = dials.weekday_earnings * workday_count
        gas = dials.weekday_earnings * dials.gas_pct * workday_count
        total_bills = sum(b.amount for b in dials.bills)
        leftover = income - gas - total_bills

        event = {
            "month": first_ts.strftime("%Y-%m"),
            "workday_count": workday_count,
            "est_income": round(income, 2),
            "est_gas": round(gas, 2),
            "total_bills": total_bills,
            "leftover": round(leftover, 2),
            "annualized_leftover": round(leftover * 12, 2),
        }
        result["events"].append(event)
        if k == 0:
            result["first_date"] = first_ts.date()
            result["last_date"] = last_ts.date()
            result["income"] = income
            result["gas"] = gas
            result["leftover"] = leftover
    return result
