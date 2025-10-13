from __future__ import annotations

import calendar
from datetime import date
from functools import lru_cache

from dateutil.relativedelta import relativedelta

from cashsim.constants import CARD_ACT_MIN_DAYS


def clamp_day(year: int, month: int, day: int) -> int:
    last = calendar.monthrange(year, month)[1]
    return min(day, last)


def next_due_date(today: date, usual_day: int) -> date:
    cand = date(today.year, today.month, clamp_day(today.year, today.month, usual_day))
    if cand >= today:
        return cand
    nxt = today + relativedelta(months=+1)
    return date(nxt.year, nxt.month, clamp_day(nxt.year, nxt.month, usual_day))


@lru_cache(maxsize=4096)
def next_due_date_cached(today: date, usual_day: int) -> date:
    """LRU-cached wrapper; safe because inputs are hashable and function is pure."""
    return next_due_date(today, usual_day)


def prior_statement_day(due_day: int) -> int:
    return max(1, due_day - CARD_ACT_MIN_DAYS)


def next_statement_close_date(today: date, due_day: int, statement_day: int | None) -> date:
    sd = statement_day or prior_statement_day(due_day)
    cand = date(today.year, today.month, clamp_day(today.year, today.month, sd))
    if cand >= today:
        return cand
    nxt = today + relativedelta(months=+1)
    return date(nxt.year, nxt.month, clamp_day(nxt.year, nxt.month, sd))


def last_statement_close_date(today: date, due_day: int, statement_day: int | None) -> date:
    ns = next_statement_close_date(today, due_day, statement_day)
    if ns > today:
        from_prev = ns + relativedelta(months=-1)
        sd = statement_day or prior_statement_day(due_day)
        return date(from_prev.year, from_prev.month, clamp_day(from_prev.year, from_prev.month, sd))
    return ns
