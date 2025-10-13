from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class SimMetrics:
    min_balance: float
    min_balance_date: Optional[date]
    first_negative_date: Optional[date]
    total_upcoming_bills: float
    friend_ask_needed: float
    friend_ask_latest_date: Optional[date]
    cushion_breach_date: Optional[date]
    accrued_interest_estimate: float
