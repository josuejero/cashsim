from __future__ import annotations

from datetime import date

import pandas as pd

from cashsim.models import Dials


def monthly_snapshot(dials: Dials, months: int = 1) -> dict:
    """Daily earnings semantics: 7d/week."""
    months = max(1, min(6, int(months)))
    today = date.today()
    result: dict = {"months": []}

    for k in range(months):
        first_ts = (pd.Timestamp(today).to_period("M") + k).to_timestamp()
        first_d = first_ts.date()
        last_d = (first_ts + pd.offsets.MonthEnd(0)).date()
        day_count = (last_d - first_d).days + 1
        income = day_count * float(dials.weekday_earnings)
        gas = income * float(dials.gas_pct)
        total_bills = round(sum(b.amount for b in dials.bills), 2)
        leftover = income - (gas + total_bills)
        result["months"].append(
            {
                "month": first_ts.strftime("%Y-%m"),
                "workday_count": day_count,
                "est_income": round(income, 2),
                "est_gas": round(gas, 2),
                "total_bills": total_bills,
                "leftover": round(leftover, 2),
                "annualized_leftover": round(leftover * 12, 2),
            }
        )
    return result
