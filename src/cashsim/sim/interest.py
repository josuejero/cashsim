from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

from cashsim.models import CreditCard
from cashsim.utils.date_utils import next_due_date, next_statement_close_date
from cashsim.utils.money import round_cents


def accrue_adb_daily(card_state: Dict[str, Dict], cards: List[CreditCard]) -> None:
    for c in cards:
        st = card_state[c.name]
        st["adb_sum"] += c.balance
        st["adb_days"] += 1
        st["unposted_interest_est"] += (c.apr / 365.0) * c.balance


def post_statement_charges_and_advance(
    day: date, card_state: Dict[str, Dict], cards: List[CreditCard]
) -> List[Tuple[str, float]]:
    """Post ADB finance charges on statement close, lock min due, advance cycle."""
    events: List[Tuple[str, float]] = []
    for c in cards:
        st = card_state[c.name]
        if day == st["next_stmt"]:
            i_amt = 0.0
            if st["adb_days"] > 0 and c.apr > 0 and c.balance > 0:
                avg_daily = st["adb_sum"] / st["adb_days"]
                # Quantize to cents with half-up — avoid binary float drifts
                i_amt = round_cents(avg_daily * (c.apr / 365.0) * st["adb_days"])
                if i_amt > 0:
                    c.balance = round(c.balance + i_amt, 2)
                    events.append((c.name, i_amt))

            st["statement_balance"] = c.balance
            st["min_due_locked"] = max(c.min_floor, round(st["statement_balance"] * c.min_pct, 2))
            st["next_stmt"] = next_statement_close_date(
                day + timedelta(days=1), c.due_day, c.statement_day
            )
            st["cycle_due"] = next_due_date(day + timedelta(days=1), c.due_day)
            st["adb_sum"] = 0.0
            st["adb_days"] = 0
            st["payments_since_stmt"] = 0.0
            st["unposted_interest_est"] = 0.0
    return events


def post_simple_interest_if_due(
    day: date, last_post: Dict[str, date], cards: List[CreditCard]
) -> List[Tuple[str, float]]:
    """Legacy: post interest on due date using days elapsed."""
    out: List[Tuple[str, float]] = []
    for c in cards:
        if next_due_date(day, c.due_day) == day and c.balance > 0 and c.apr > 0:
            days_elapsed = max(0, (day - last_post[c.name]).days)
            if days_elapsed > 0:
                i_amt = round_cents(c.balance * (c.apr / 365.0) * days_elapsed)
                c.balance = round(c.balance + i_amt, 2)
                out.append((c.name, i_amt))
                last_post[c.name] = day
    return out
