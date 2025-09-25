from __future__ import annotations

from datetime import date

from cashsim.models import Bill
from cashsim.utils.date_utils import next_due_date_cached as next_due_date


def roll_bills(today: date, bills: list[Bill]) -> list[tuple[Bill, date]]:
    rolled = []
    for b in bills:
        d = next_due_date(today, b.usual_day)
        rolled.append((b, d))
    rolled.sort(key=lambda t: t[1])
    return rolled


def sum_non_debt_bills_due_today(day: date, bills: list[Bill]) -> float:
    total = 0.0
    for b in bills:
        if next_due_date(day, b.usual_day) == day:
            total += b.amount
    return round(total, 2)
