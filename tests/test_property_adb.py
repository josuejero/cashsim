from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from cashsim.utils.money import D, quantize_cents


def _adb_interest(daily_balances: list[Decimal], apr: Decimal) -> Decimal:
    """interest = average_daily_balance × daily_rate × days_in_cycle"""
    days = Decimal(len(daily_balances))
    daily_rate = D(apr) / D(365)
    adb = sum((D(b) for b in daily_balances), D("0")) / days
    return quantize_cents(adb * daily_rate * days)


@given(
    daily=st.lists(st.decimals(min_value=0, max_value=10000, places=2), min_size=1, max_size=31),
    apr=st.decimals(min_value=0, max_value=Decimal("0.5"), places=4),
)
def test_adb_identity_property(daily: list[Decimal], apr: Decimal) -> None:
    # Identity: sum(balances) * daily_rate  ==  ADB * daily_rate * days
    daily = [Decimal(str(x)) for x in daily]
    daily_rate = D(apr) / D(365)
    lhs = quantize_cents(sum((D(b) * daily_rate for b in daily), D("0")))
    rhs = _adb_interest(daily, apr)
    assert lhs == rhs
