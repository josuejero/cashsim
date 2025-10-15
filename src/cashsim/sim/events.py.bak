from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple


def add_finance_event(
    events: List[dict], day: date, account: str, amt: float, new_balance: float
) -> None:
    events.append(
        {
            "date": day,
            "account": account,
            "finance_charge": amt,
            "minimum_paid": 0.0,
            "extra_paid": 0.0,
            "new_balance": new_balance,
        }
    )


def add_min_event(
    events: List[dict], day: date, account: str, amt: float, new_balance: float
) -> None:
    events.append(
        {
            "date": day,
            "account": account,
            "finance_charge": 0.0,
            "minimum_paid": amt,
            "extra_paid": 0.0,
            "new_balance": new_balance,
        }
    )


def add_extra_event(
    events: List[dict],
    day: date,
    account: str,
    extra: float,
    new_balance: float,
    *,
    surplus_used: float,
    reserve_needed: float,
    reserve_7d_bills: float,
    reserve_7d_mins: float,
    reserve_7d_gas: float,
) -> None:
    events.append(
        {
            "date": day,
            "account": account,
            "finance_charge": 0.0,
            "minimum_paid": 0.0,
            "extra_paid": extra,
            "new_balance": new_balance,
            "surplus_used": surplus_used,
            "reserve_needed": reserve_needed,
            "reserve_7d_bills": reserve_7d_bills,
            "reserve_7d_mins": reserve_7d_mins,
            "reserve_7d_gas": reserve_7d_gas,
        }
    )
