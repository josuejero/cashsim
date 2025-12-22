from __future__ import annotations

from datetime import date, timedelta

from cashsim.models import Dials

FEATURE_COLUMNS: list[str] = [
    "starting_balance",
    "safety_cushion",
    "weekday_earnings",
    "total_monthly_bills",
    "total_debt_balance",
    "total_debt_minimum",
    "oneoff_total_horizon",
    "gas_pct",
    "gas_fill_size",
    "num_bills",
    "num_debts",
    "num_oneoffs",
]


def _min_payment(balance: float, *, min_pct: float, min_floor: float) -> float:
    return float(max(min_floor, balance * min_pct))


def featurize_dials(dials: Dials, *, start: date, horizon_days: int) -> dict[str, float]:
    """Compute explainable, stable features from inputs.

    Keep this logic aligned between training and serving.
    """
    end = start + timedelta(days=horizon_days)

    total_monthly_bills = float(sum(b.amount for b in dials.bills))

    cc_min = sum(
        _min_payment(c.balance, min_pct=c.min_pct, min_floor=c.min_floor)
        for c in dials.credit_cards
    )
    iou_min = sum(
        _min_payment(i.balance, min_pct=i.min_pct, min_floor=i.min_floor) for i in dials.ious
    )

    total_debt_balance = float(
        sum(c.balance for c in dials.credit_cards) + sum(i.balance for i in dials.ious)
    )
    total_debt_minimum = float(cc_min + iou_min)

    oneoff_total = float(sum(o.amount for o in dials.oneoffs if start <= o.due_date < end))

    num_bills = float(len(dials.bills))
    num_debts = float(len(dials.credit_cards) + len(dials.ious))
    num_oneoffs = float(len(dials.oneoffs))

    feats: dict[str, float] = {
        "starting_balance": float(dials.current_cash),
        "safety_cushion": float(dials.safety_cushion),
        "weekday_earnings": float(dials.weekday_earnings),
        "total_monthly_bills": total_monthly_bills,
        "total_debt_balance": total_debt_balance,
        "total_debt_minimum": total_debt_minimum,
        "oneoff_total_horizon": oneoff_total,
        "gas_pct": float(dials.gas_pct),
        "gas_fill_size": float(dials.gas_fill_size),
        "num_bills": num_bills,
        "num_debts": num_debts,
        "num_oneoffs": num_oneoffs,
    }

    return {k: float(feats.get(k, 0.0)) for k in FEATURE_COLUMNS}
