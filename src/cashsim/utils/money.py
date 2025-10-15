from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# One "cent" quantum for money rounding.
CENT = Decimal("0.01")


def D(x: float | int | str | Decimal) -> Decimal:
    """Safe Decimal constructor (avoid binary float artifacts)."""
    return x if isinstance(x, Decimal) else Decimal(str(x))


def quantize_cents(x: Decimal, *, rounding: str = ROUND_HALF_UP) -> Decimal:
    """Quantize a Decimal to cents with an explicit rounding mode."""
    return D(x).quantize(CENT, rounding=rounding)


def to_cents(x: float | str | Decimal) -> int:
    """
    Convert a dollar amount to integer cents using HALF_UP.
    Use only at I/O boundaries (storage, display, external APIs).
    """
    return int(quantize_cents(D(x), rounding=ROUND_HALF_UP) * 100)


def from_cents(c: int) -> float:
    """Convert integer cents back to float dollars representation (display only)."""
    return float(Decimal(int(c)) / 100)


def round_cents(x: float | str | Decimal) -> float:
    """
    Round a dollar amount to two decimals (HALF_UP) and return float.
    Prefer doing all intermediate arithmetic with Decimal, then call this when
    you must hand a float to existing models/fields.
    """
    return float(quantize_cents(D(x), rounding=ROUND_HALF_UP))


# --- Drop-in helpers (Decimal everywhere for interest posting) ---
# See: Python decimal & quantize for exact-money rounding (HALF_UP is typical for statements).
# https://docs.python.org/3/library/decimal.html
def round_money(x: Decimal) -> Decimal:
    return quantize_cents(D(x), rounding=ROUND_HALF_UP)


def post_daily_interest(balance: Decimal, apr: Decimal) -> Decimal:
    daily_rate = D(apr) / D("365")
    return round_money(D(balance) * daily_rate)
