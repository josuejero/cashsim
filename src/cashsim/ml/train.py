from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

import joblib
import mlflow
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_COLUMNS


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _build_model(model_type: str, *, params: dict) -> Pipeline:
    if model_type == "logreg":
        clf = LogisticRegression(
            C=float(params.get("C", 1.0)),
            max_iter=int(params.get("max_iter", 2000)),
            solver="lbfgs",
            n_jobs=None,
        )
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("model", clf),
            ]
        )

    if model_type == "gbdt":
        clf = GradientBoostingClassifier(
            n_estimators=int(params.get("n_estimators", 300)),
            max_depth=int(params.get("max_depth", 3)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            random_state=0,
        )
        # keep scaler for stable contribution reporting interface even though not strictly needed
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("model", clf),
            ]
        )

    raise ValueError(f"Unknown model_type={model_type!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Train overdraft-risk model.")
    ap.add_argument("--data", required=True, help="Input Parquet")
    ap.add_argument("--model", required=True, help="Output model joblib")
    ap.add_argument("--feature-names", required=True, help="Output feature_names.json")
    ap.add_argument("--meta", required=True, help="Output training_meta.json")
    args = ap.parse_args()

    import yaml

    params = yaml.safe_load(Path("params.yaml").read_text()) if Path("params.yaml").exists() else {}
    rp = params.get("risk", {})

    seed = int(rp.get("seed", 1337))
    test_size = float(rp.get("test_size", 0.2))
    model_type = str(rp.get("model_type", "logreg"))
    model_params = dict(rp.get(model_type, {}))

    df = pd.read_parquet(args.data)
    X = df[FEATURE_COLUMNS]
    y = df["label_overdraft"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=seed,
        stratify=y if y.nunique() > 1 else None,
    )

    # Train outside the MLflow run context, so we don't end up with empty/partial runs.
    pipe = _build_model(model_type, params=model_params)
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, proba)) if y_test.nunique() > 1 else float("nan")
    brier = float(brier_score_loss(y_test, proba))

    model_path = Path(args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, model_path)

    Path(args.feature_names).write_text(json.dumps(FEATURE_COLUMNS, indent=2))

    meta = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "git_sha": _git_sha(),
        "data": str(Path(args.data)),
        "n_rows": int(len(df)),
        "model_type": model_type,
        "model_params": model_params,
        "seed": seed,
        "test_size": test_size,
        "metrics": {"auc": auc, "brier": brier},
    }
    Path(args.meta).parent.mkdir(parents=True, exist_ok=True)
    Path(args.meta).write_text(json.dumps(meta, indent=2))

    # MLflow logging
    mlflow.set_experiment("cashsim-risk")

    with mlflow.start_run(run_name=f"risk-{model_type}"):
        mlflow.log_params(
            {"model_type": model_type, **{f"{model_type}.{k}": v for k, v in model_params.items()}}
        )
        mlflow.log_params({"seed": seed, "test_size": test_size})
        mlflow.log_metrics({"auc": auc, "brier": brier})
        mlflow.log_artifact(str(Path(args.meta)))
        mlflow.log_artifact(str(Path(args.feature_names)))
        mlflow.log_artifact(str(model_path))


if __name__ == "__main__":
    main()
