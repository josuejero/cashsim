from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

from cashsim.models import IOU, Bill, CreditCard, Dials, OneOff
from cashsim.utils.date_utils import (
    last_statement_close_date,
    next_statement_close_date,
)
from cashsim.utils.date_utils import (
    next_due_date_cached as next_due_date,
)

from .events import add_extra_event, add_finance_event, add_min_event
from .gas import apply_gas_skim_and_fillups
from .interest import (
    accrue_adb_daily,
    post_simple_interest_if_due,
    post_statement_charges_and_advance,
)
from .reserve import reserve_next_7_days
from .roll import sum_non_debt_bills_due_today
from .types import SimMetrics


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")


def simulate_month(
    dials: Dials, *, start: date | None = None, days: int = 31
) -> tuple[pd.DataFrame, SimMetrics]:
    start = start or date.today()

    bills: list[Bill] = list(dials.bills)
    cards: list[CreditCard] = [CreditCard(**c.model_dump()) for c in dials.credit_cards]
    ious: list[IOU] = [IOU(**x.model_dump()) for x in dials.ious]
    oneoffs: list[OneOff] = [OneOff(**o.model_dump()) for o in getattr(dials, "oneoffs", [])]

    # per-card state
    card_state: dict[str, dict] = {}
    for c in cards:
        cycle_start = last_statement_close_date(start, c.due_day, c.statement_day)
        next_stmt = next_statement_close_date(start, c.due_day, c.statement_day)
        cycle_due = next_due_date(next_stmt + timedelta(days=1), c.due_day)
        card_state[c.name] = {
            "cycle_start": cycle_start,
            "next_stmt": next_stmt,
            "cycle_due": cycle_due,
            "adb_sum": 0.0,
            "adb_days": 0,
            "statement_balance": None,
            "min_due_locked": None,
            "grace_active": (c.balance <= 0.0),
            "payments_since_stmt": 0.0,
            "unposted_interest_est": 0.0,
        }

    oneoff_saved: dict[str, float] = {o.name: 0.0 for o in oneoffs}
    oneoff_paid: dict[str, bool] = {o.name: False for o in oneoffs}

    records: list[dict] = []
    gas_bucket = 0.0
    balance = float(dials.current_cash)
    min_balance = balance
    min_balance_date: date | None = start
    first_negative: date | None = None
    cushion_breach_date: date | None = None

    paid_non_debt_bills = 0.0
    paid_cc_mins = 0.0
    paid_iou_mins = 0.0
    paid_oneoffs_total = 0.0

    last_interest_post_simple: dict[str, date] = {c.name: start for c in cards}

    for i in range(days):
        day = start + timedelta(days=i)
        earn = float(dials.weekday_earnings)

        # GAS
        balance, gas_bucket, fillups = apply_gas_skim_and_fillups(
            balance, gas_bucket, earn, dials.gas_pct, dials.gas_fill_size
        )

        # BILLS (non-debt)
        bill_due_today = sum_non_debt_bills_due_today(day, bills)
        if bill_due_today > 0:
            balance -= bill_due_today
            paid_non_debt_bills += bill_due_today

        # ---------- one-off contributions from surplus ----------
        oneoff_contrib_events: list[tuple[str, float]] = []
        total_now, _, _, gas_pred_now = reserve_next_7_days(
            day,
            bills=bills,
            cards=cards,
            ious=ious,
            oneoffs=oneoffs,
            include_today=True,
            locked_mins={},
            locked_due_dates={},
            oneoff_saved=oneoff_saved,
            gas_bucket=gas_bucket,
            daily_earn=earn,
            gas_pct=dials.gas_pct,
            fill_size=dials.gas_fill_size,
        )
        reserve_now = dials.safety_cushion + total_now
        surplus_now = round(balance - reserve_now, 2)
        if surplus_now > 0 and oneoffs:
            targets = sorted(
                [o for o in oneoffs if not oneoff_paid[o.name] and o.due_date >= day],
                key=lambda o: (-int(o.priority), o.due_date),
            )
            remaining = surplus_now
            for o in targets:
                shortfall = max(0.0, round(o.amount - oneoff_saved[o.name], 2))
                if shortfall <= 0 or remaining <= 0:
                    continue
                contrib = min(shortfall, remaining)
                oneoff_saved[o.name] = round(oneoff_saved[o.name] + contrib, 2)
                balance = round(balance - contrib, 2)
                remaining = round(remaining - contrib, 2)
                oneoff_contrib_events.append((o.name, contrib))

        # ---------- pay one-offs on due date ----------
        oneoff_paid_events: list[tuple[str, float]] = []
        for o in oneoffs:
            if (not oneoff_paid[o.name]) and (day == o.due_date):
                use_saved = min(oneoff_saved[o.name], o.amount)
                from_balance = round(o.amount - use_saved, 2)
                oneoff_saved[o.name] = round(oneoff_saved[o.name] - use_saved, 2)
                if from_balance > 0:
                    balance = round(balance - from_balance, 2)
                oneoff_paid[o.name] = True
                oneoff_paid_events.append((o.name, o.amount))
                paid_oneoffs_total = round(paid_oneoffs_total + o.amount, 2)

        # ---------- cards ----------
        interest_events: list[tuple[str, float]] = []
        minpay_events: list[tuple[str, float]] = []
        extra_on_due_events: list[tuple[str, float]] = []
        unified_events: list[dict] = []

        if dials.interest_mode == "statement_adb":
            accrue_adb_daily(card_state, cards)

        if dials.interest_mode == "statement_adb":
            for acc, amt in post_statement_charges_and_advance(day, card_state, cards):
                interest_events.append((acc, amt))
                # event entry
                for c in cards:
                    if c.name == acc:
                        add_finance_event(unified_events, day, acc, amt, c.balance)
                        break

        # due date: mins + extras
        due_today = [c for c in cards if next_due_date(day, c.due_day) == day and c.balance > 0]
        if due_today:
            locked_mins = {
                n: st["min_due_locked"]
                for n, st in card_state.items()
                if st["min_due_locked"] is not None
            }

            # minimums
            for c in due_today:
                locked = locked_mins.get(c.name)
                due_min = (
                    locked
                    if locked is not None
                    else max(c.min_floor, round(c.balance * c.min_pct, 2))
                )
                pay_min = min(due_min, c.balance)
                if pay_min > 0:
                    c.balance = round(c.balance - pay_min, 2)
                    balance = round(balance - pay_min, 2)
                    paid_cc_mins += pay_min
                    minpay_events.append((c.name, pay_min))
                    add_min_event(unified_events, day, c.name, pay_min, c.balance)
                    if dials.interest_mode == "statement_adb":
                        card_state[c.name]["payments_since_stmt"] += pay_min

            locked_due = {
                n: st["cycle_due"]
                for n, st in card_state.items()
                if st["min_due_locked"] is not None
            }
            total7, bills7, mins7, gas7 = reserve_next_7_days(
                day,
                bills=bills,
                cards=cards,
                ious=ious,
                oneoffs=oneoffs,
                include_today=False,
                locked_mins=locked_mins,
                locked_due_dates=locked_due,
                oneoff_saved=oneoff_saved,
                gas_bucket=gas_bucket,
                daily_earn=earn,
                gas_pct=dials.gas_pct,
                fill_size=dials.gas_fill_size,
            )
            reserve_need = dials.safety_cushion + total7
            surplus = round(balance - reserve_need, 2)

            if dials.extra_strategy == "avalanche":
                due_today.sort(key=lambda c: c.apr, reverse=True)
            else:
                due_today.sort(key=lambda c: c.balance)

            remaining = surplus
            for c in due_today:
                if remaining <= 0 or c.balance <= 0:
                    break
                extra = min(remaining, c.balance)
                if extra > 0:
                    c.balance = round(c.balance - extra, 2)
                    balance = round(balance - extra, 2)
                    remaining = round(remaining - extra, 2)
                    extra_on_due_events.append((c.name, extra))
                    add_extra_event(
                        unified_events,
                        day,
                        c.name,
                        extra,
                        c.balance,
                        surplus_used=extra,
                        reserve_needed=reserve_need,
                        reserve_7d_bills=bills7,
                        reserve_7d_mins=mins7,
                        reserve_7d_gas=gas7,
                    )
                    if dials.interest_mode == "statement_adb":
                        card_state[c.name]["payments_since_stmt"] += extra

            # set grace flags
            if dials.interest_mode == "statement_adb":
                for c in due_today:
                    st = card_state[c.name]
                    if st["statement_balance"] is not None:
                        st["grace_active"] = (st["payments_since_stmt"] + 1e-9) >= (
                            st["statement_balance"] - 1e-9
                        )

        if dials.interest_mode == "due_simple":
            for acc, amt in post_simple_interest_if_due(day, last_interest_post_simple, cards):
                interest_events.append((acc, amt))
                for c in cards:
                    if c.name == acc:
                        add_finance_event(unified_events, day, acc, amt, c.balance)
                        break

        # extremes
        if balance < min_balance:
            min_balance = balance
            min_balance_date = day
        if first_negative is None and balance < 0:
            first_negative = day
        if cushion_breach_date is None and balance < dials.safety_cushion:
            cushion_breach_date = day

        accrued_est = 0.0
        if dials.interest_mode == "statement_adb":
            accrued_est = round(sum(st["unposted_interest_est"] for st in card_state.values()), 2)

        row: dict = {
            "date": day,
            "weekday": day.strftime("%a"),
            "earn": round(earn, 2),
            "bill_due": round(bill_due_today, 2),
            "balance": round(balance, 2),
            "gas_bucket": round(gas_bucket, 2),
            "fillups": int(fillups),
            "cc_events": unified_events,
            "cc_interest_posted": interest_events,
            "cc_min_paid": minpay_events,
            "cc_extra_on_due": extra_on_due_events,
            "oneoff_contribs": oneoff_contrib_events,
            "oneoff_paid": oneoff_paid_events,
            "total_cc_balance": round(sum(c.balance for c in cards), 2),
            "total_iou_balance": round(sum(x.balance for x in ious), 2),
            "accrued_interest_unposted": accrued_est,
        }
        for c in cards:
            row[f"cc_{_slug(c.name)}_bal"] = round(c.balance, 2)
        records.append(row)

    df = pd.DataFrame.from_records(records)

    if min_balance < 0:
        friend_ask_needed = round(-min_balance, 2)
        friend_ask_latest_date = first_negative
    else:
        friend_ask_needed = 0.0
        friend_ask_latest_date = None

    total_upcoming_bills = round(
        paid_non_debt_bills + paid_cc_mins + paid_iou_mins + paid_oneoffs_total, 2
    )

    metrics = SimMetrics(
        min_balance=round(min_balance, 2),
        min_balance_date=min_balance_date,
        first_negative_date=first_negative,
        total_upcoming_bills=total_upcoming_bills,
        friend_ask_needed=friend_ask_needed,
        friend_ask_latest_date=friend_ask_latest_date,
        cushion_breach_date=cushion_breach_date,
        accrued_interest_estimate=round(
            sum(st["unposted_interest_est"] for st in card_state.values()), 2
        )
        if dials.interest_mode == "statement_adb"
        else 0.0,
    )
    return df, metrics
