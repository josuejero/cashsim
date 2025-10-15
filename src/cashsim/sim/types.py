# File: src/cashsim/sim/types.py
from __future__ import annotations

# NOTE: We intentionally import NotRequired from typing_extensions so this file
# type-checks on Python < 3.11. We prevent Ruff's pyupgrade from rewriting this.
from dataclasses import dataclass
from datetime import date
from typing import Literal

from typing_extensions import NotRequired, TypedDict  # ruff: noqa


class BaseEvent(TypedDict):
    day: date
    account: str
    new_balance: float


class FinanceEvent(BaseEvent):
    kind: Literal["finance"]
    amt: float


class MinEvent(BaseEvent):
    kind: Literal["min"]
    amt: float


class ExtraEvent(BaseEvent):
    kind: Literal["extra"]
    extra: float
    surplus_used: NotRequired[float]
    reserve_needed: NotRequired[float]
    reserve_7d_bills: NotRequired[float]
    reserve_7d_mins: NotRequired[float]
    reserve_7d_gas: NotRequired[float]


Event = FinanceEvent | MinEvent | ExtraEvent


# minimal card-state shape for runtime helpers
class CardState(TypedDict, total=False):
    balance: float
    adb_days: float
    adb_sum: float
    min_due_locked: float


@dataclass
class SimMetrics:
    min_balance: float
    min_balance_date: date | None
    first_negative_date: date | None
    total_upcoming_bills: float
    friend_ask_needed: float
    friend_ask_latest_date: date | None
    cushion_breach_date: date | None
    accrued_interest_estimate: float
