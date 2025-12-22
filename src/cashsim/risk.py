from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol, cast

import joblib
import pandas as pd

from cashsim.ml.features import FEATURE_COLUMNS, featurize_dials
from cashsim.models import Dials


@dataclass(frozen=True)
class RiskDriver:
    feature: str
    contribution: float  # log-odds contribution
    direction: Literal["increases", "decreases"]
    value: float


@dataclass(frozen=True)
class RiskResult:
    probability: float
    horizon_days: int
    drivers: list[RiskDriver]


class _Pipeline(Protocol):
    def predict_proba(self, X: pd.DataFrame) -> Sequence[Sequence[float]]: ...

    @property
    def named_steps(self) -> Mapping[str, object]: ...


class _Scaler(Protocol):
    def transform(self, X: pd.DataFrame) -> Sequence[Sequence[float]]: ...


class _LinearModel(Protocol):
    coef_: Sequence[Sequence[float]]


def load_model(model_path: Path) -> _Pipeline:
    if not model_path.exists():
        raise FileNotFoundError(
            f"Risk model not found at {model_path}. "
            f"Run: dvc repro (or at least the risk_train stage) to produce it."
        )
    return joblib.load(model_path)


def predict_overdraft_risk(
    dials: Dials,
    *,
    start: date,
    horizon_days: int = 30,
    model_path: Path = Path("artifacts/risk/model.joblib"),
    top_k: int = 5,
) -> RiskResult:
    pipe = load_model(model_path)

    feats = featurize_dials(dials, start=start, horizon_days=horizon_days)
    X = pd.DataFrame([feats])[FEATURE_COLUMNS]

    proba = pipe.predict_proba(X)
    p = float(proba[0][1])

    # Explainability: approximate logistic regression drivers via coef * standardized value.
    drivers: list[RiskDriver] = []
    try:
        scaler = pipe.named_steps.get("scaler")
        model = pipe.named_steps.get("model")
        if hasattr(model, "coef_") and scaler is not None:
            scaler = cast(_Scaler, scaler)
            model = cast(_LinearModel, model)
            x_scaled = scaler.transform(X)
            x_scaled_row = x_scaled[0]
            coefs = model.coef_[0]

            pairs = []
            for i, feat in enumerate(FEATURE_COLUMNS):
                c = float(x_scaled_row[i]) * float(coefs[i])
                pairs.append((feat, c, float(X.iloc[0][feat])))

            pairs.sort(key=lambda t: abs(t[1]), reverse=True)
            for feat, c, val in pairs[: max(1, top_k)]:
                direction: Literal["increases", "decreases"] = "increases" if c > 0 else "decreases"
                drivers.append(
                    RiskDriver(
                        feature=feat,
                        contribution=c,
                        direction=direction,
                        value=val,
                    )
                )
    except Exception:
        # If explainability fails for any reason, we still return the probability.
        drivers = []

    return RiskResult(probability=p, horizon_days=horizon_days, drivers=drivers)
