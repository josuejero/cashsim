from __future__ import annotations


def apply_gas_skim_and_fillups(
    balance: float,
    gas_bucket: float,
    daily_earn: float,
    gas_pct: float,
    fill_size: float,
) -> tuple[float, float, int]:
    """
    Skim daily gas, accumulate bucket, execute fill-ups (withdraw from balance).
    O(1) arithmetic version (no loop). Returns (new_balance, new_gas_bucket, fillups_count).
    """
    gas_skim = daily_earn * gas_pct
    new_bucket = gas_bucket + gas_skim

    fills_before = int(gas_bucket // fill_size)
    fills_after = int(new_bucket // fill_size)
    fills = max(0, fills_after - fills_before)

    balance -= fills * fill_size
    gas_bucket = new_bucket - fills * fill_size
    balance += daily_earn - gas_skim
    return round(balance, 2), round(gas_bucket, 2), fills


def predict_fill_cost_7d(
    gas_bucket: float, daily_earn: float, gas_pct: float, fill_size: float
) -> float:
    """
    Conservative predictor for gas spend within 7 days:
    count how many fillups will be triggered by 7 days worth of skims.
    """
    if fill_size <= 0:
        return 0.0
    added = 7.0 * daily_earn * gas_pct
    start_fills = int(gas_bucket // fill_size)
    end_fills = int((gas_bucket + added) // fill_size)
    new_fills = max(0, end_fills - start_fills)
    return round(new_fills * fill_size, 2)
