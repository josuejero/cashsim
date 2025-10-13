from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
