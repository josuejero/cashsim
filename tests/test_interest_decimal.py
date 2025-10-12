from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
from cashsim.utils.money import D, quantize_cents

def test_rounding_modes_examples():
    # .5 ties differ by mode: HALF_UP vs HALF_EVEN ("banker's")
    assert quantize_cents(Decimal("1.005"), rounding=ROUND_HALF_UP) == Decimal("1.01")
    assert quantize_cents(Decimal("1.015"), rounding=ROUND_HALF_EVEN) == Decimal("1.02")

def test_adb_property_equivalence():
    # ADB identity:
    # interest = average_daily_balance × daily_rate × days_in_cycle
    # average_daily_balance = sum(daily_balances)/days_in_cycle
    # => same as quantize(sum(daily_balances) * daily_rate)
    daily = [Decimal("100.00")]*15 + [Decimal("200.00")]*15
    days = Decimal(len(daily))
    apr = Decimal("0.2199")
    daily_rate = apr / Decimal(365)
    adb = sum(daily)/days

    i1 = quantize_cents(adb * daily_rate * days, rounding=ROUND_HALF_UP)
    i2 = quantize_cents(sum(b * daily_rate for b in daily), rounding=ROUND_HALF_UP)
    assert i1 == i2
