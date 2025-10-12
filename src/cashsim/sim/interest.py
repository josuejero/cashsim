from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

from cashsim.models import CreditCard
from cashsim.utils.date_utils import next_due_date, next_statement_close_date
from cashsim.utils.money import D, quantize_cents, round_cents

def accrue_adb_daily(card_state: Dict[str, Dict], cards: List[CreditCard]) -> None:
    """
    Accumulate ADB using Decimal internally for interest math.
    Store back as floats to maintain compatibility with existing code.
    """
    for c in cards:
        st = card_state[c.name]
        st["adb_sum"] = float(D(st.get("adb_sum", 0)) + D(c.balance))
        st["adb_days"] = int(st.get("adb_days", 0)) + 1
        # Unposted interest estimate (not booked): (APR/365) * balance
        st["unposted_interest_est"] = float(
            D(st.get("unposted_interest_est", 0)) + (D(c.apr) / D(365)) * D(c.balance)
        )

def post_statement_charges_and_advance(
    day: date, card_state: Dict[str, Dict], cards: List[CreditCard]
) -> List[Tuple[str, float]]:
    """
    Post ADB finance charges on statement close, lock min due, advance cycle.
    Interest is computed with Decimal and quantized to cents using HALF_UP,
    which is typical for consumer statements. Switch to ROUND_HALF_EVEN only
    if you explicitly choose banker's rounding and document why.
    """
    events: List[Tuple[str, float]] = []
    for c in cards:
        st = card_state[c.name]
        if day == st["next_stmt"]:
            if st.get("adb_days", 0) > 0 and c.apr > 0 and c.balance > 0:
                avg_daily = D(st["adb_sum"]) / D(st["adb_days"])
                daily_rate = D(c.apr) / D(365)
                i_dec = quantize_cents(avg_daily * daily_rate * D(st["adb_days"]), rounding=ROUND_HALF_UP)
                i_amt = float(i_dec)
                if i_amt > 0:
                    c.balance = round_cents(D(c.balance) + i_dec)
                    events.append((c.name, i_amt))

            st["statement_balance"] = c.balance
            min_from_pct = float(quantize_cents(D(st["statement_balance"]) * D(c.min_pct), rounding=ROUND_HALF_UP))
            st["min_due_locked"] = max(c.min_floor, min_from_pct)
            st["next_stmt"] = next_statement_close_date(day + timedelta(days=1), c.due_day, c.statement_day)
            st["cycle_due"] = next_due_date(day + timedelta(days=1), c.due_day)
            st["adb_sum"] = 0.0
            st["adb_days"] = 0
            st["payments_since_stmt"] = 0.0
            st["unposted_interest_est"] = 0.0
    return events

def post_simple_interest_if_due(
    day: date, last_post: Dict[str, date], cards: List[CreditCard]
) -> List[Tuple[str, float]]:
    """Legacy: post interest on due date using days elapsed (Decimal math)."""
    out: List[Tuple[str, float]] = []
    for c in cards:
        if next_due_date(day, c.due_day) == day and c.balance > 0 and c.apr > 0:
            days_elapsed = max(0, (day - last_post[c.name]).days)
            if days_elapsed > 0:
                i_dec = quantize_cents(D(c.balance) * (D(c.apr) / D(365)) * D(days_elapsed), rounding=ROUND_HALF_UP)
                c.balance = round_cents(D(c.balance) + i_dec)
                out.append((c.name, float(i_dec)))
                last_post[c.name] = day
    return out
