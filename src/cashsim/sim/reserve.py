from __future__ import annotations

from datetime import date, timedelta

from cashsim.models import IOU, Bill, CreditCard, OneOff
from cashsim.utils.date_utils import next_due_date_cached as next_due_date

from .gas import predict_fill_cost_7d


def reserve_next_7_days(
    start_day: date,
    *,
    bills: list[Bill],
    cards: list[CreditCard],
    ious: list[IOU],
    oneoffs: list[OneOff],
    include_today: bool,
    locked_mins: dict[str, float] | None = None,
    locked_due_dates: dict[str, date] | None = None,
    oneoff_saved: dict[str, float] | None = None,
    gas_bucket: float = 0.0,
    daily_earn: float = 0.0,
    gas_pct: float = 0.0,
    fill_size: float = 1.0,
) -> tuple[float, float, float, float]:
    """
    7-day reserve = non-debt bills + CC/IOU minimums + one-off shortfalls + predicted gas fills.
    Returns (total, nondebt, debt_mins, gas_pred).
    """
    horizon_end = start_day + timedelta(days=6)
    left_bound = start_day if include_today else (start_day + timedelta(days=1))

    amt_bills = 0.0
    amt_mins = 0.0

    for b in bills:
        due = next_due_date(start_day, b.usual_day)
        if left_bound <= due <= horizon_end:
            amt_bills += b.amount

    if oneoffs:
        for o in oneoffs:
            due = o.due_date
            if left_bound <= due <= horizon_end:
                saved = (oneoff_saved or {}).get(o.name, 0.0)
                shortfall = max(0.0, round(o.amount - saved, 2))
                amt_bills += shortfall

    for c in cards:
        due = (locked_due_dates or {}).get(c.name) or next_due_date(start_day, c.due_day)
        if left_bound <= due <= horizon_end:
            if locked_mins and c.name in locked_mins:
                due_min = locked_mins[c.name]
            else:
                due_min = max(c.min_floor, round(c.balance * c.min_pct, 2))
            amt_mins += due_min

    for x in ious:
        if x.due_day is None:
            continue
        due = next_due_date(start_day, x.due_day)
        if left_bound <= due <= horizon_end:
            due_min = max(x.min_floor, round(x.balance * x.min_pct, 2))
            amt_mins += due_min

    gas_pred = predict_fill_cost_7d(gas_bucket, daily_earn, gas_pct, fill_size)
    total = round(amt_bills + amt_mins + gas_pred, 2)
    return total, round(amt_bills, 2), round(amt_mins, 2), round(gas_pred, 2)
