from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def to_cents(x: float | str) -> int:
    """Convert a float/str dollar amount to integer cents (half-up)."""
    return int((Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP) * 100))


def from_cents(c: int) -> float:
    """Convert integer cents back to a float dollars representation."""
    return float(Decimal(c) / 100)


def round_cents(x: float | str | Decimal) -> float:
    """Round a dollar amount to 2 decimals (half-up) and return float."""
    return float(Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP))
