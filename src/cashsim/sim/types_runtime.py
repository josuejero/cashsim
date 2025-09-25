from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CardRT:
    """Runtime-lean card structure for hot loops (validated at the edges)."""
    name: str
    apr: float
    balance_cents: int
    due_day: int
    min_pct: float
    min_floor_cents: int
    statement_day: int | None
