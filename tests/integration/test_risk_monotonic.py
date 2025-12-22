from __future__ import annotations

from datetime import date
from pathlib import Path

from cashsim.models import Dials
from cashsim.risk import predict_overdraft_risk


def test_more_cash_should_not_increase_risk(tmp_path: Path) -> None:
    model_path = Path("artifacts/risk/model.joblib")
    if not model_path.exists():
        return

    base = Dials(
        current_cash=200,
        safety_cushion=150,
        weekday_earnings=80,
        gas_pct=0.1,
        gas_fill_size=25,
        bills=[],
        credit_cards=[],
        ious=[],
        oneoffs=[],
    )
    richer = base.model_copy(update={"current_cash": 400})

    p1 = predict_overdraft_risk(
        base, start=date(2025, 1, 1), horizon_days=30, model_path=model_path
    ).probability
    p2 = predict_overdraft_risk(
        richer, start=date(2025, 1, 1), horizon_days=30, model_path=model_path
    ).probability

    assert p2 <= p1 + 0.02
