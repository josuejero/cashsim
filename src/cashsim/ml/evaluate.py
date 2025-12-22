from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, roc_auc_score

from .features import FEATURE_COLUMNS


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate overdraft-risk model.")
    ap.add_argument("--data", required=True, help="Input Parquet")
    ap.add_argument("--model", required=True, help="Model joblib")
    ap.add_argument("--outdir", required=True, help="Output directory")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.data)
    X = df[FEATURE_COLUMNS]
    y = df["label_overdraft"].astype(int)

    pipe = joblib.load(args.model)
    proba = pipe.predict_proba(X)[:, 1]

    auc = float(roc_auc_score(y, proba)) if y.nunique() > 1 else float("nan")
    brier = float(brier_score_loss(y, proba))

    frac_pos, mean_pred = calibration_curve(y, proba, n_bins=10, strategy="quantile")

    metrics = {
        "auc": auc,
        "brier": brier,
        "calibration_bins": int(len(frac_pos)),
        "calibration": [
            {"bin": int(i), "mean_pred": float(mean_pred[i]), "frac_pos": float(frac_pos[i])}
            for i in range(len(frac_pos))
        ],
    }

    (outdir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    plt.figure()
    plt.plot([0, 1], [0, 1])
    plt.plot(mean_pred, frac_pos)
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Fraction of positives")
    plt.title("Calibration curve")
    plt.tight_layout()
    plt.savefig(outdir / "calibration.png")


if __name__ == "__main__":
    main()
