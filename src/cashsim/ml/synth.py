from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from cashsim.models import IOU, Bill, CreditCard, Dials, OneOff
from cashsim.sim.core import simulate_month

from .features import FEATURE_COLUMNS, featurize_dials


def _parse_date(s: str) -> date:
    return date.fromisoformat(s)


def _rng_float(rng: random.Random, a: float, b: float) -> float:
    return float(round(rng.uniform(a, b), 2))


def _mk_dials(rng: random.Random, *, start: date, horizon_days: int) -> Dials:
    current_cash = _rng_float(rng, 0, 2500)
    safety_cushion = _rng_float(rng, 0, 1500)
    weekday_earnings = _rng_float(rng, 0, 300)
    gas_pct = float(round(rng.uniform(0.05, 0.25), 3))
    gas_fill_size = _rng_float(rng, 10, 70)

    bills: list[Bill] = []
    for i in range(rng.randint(0, 5)):
        bills.append(
            Bill(
                name=f"bill_{i}",
                amount=_rng_float(rng, 20, 900),
                usual_day=rng.randint(1, 28),
            )
        )

    ccs: list[CreditCard] = []
    for i in range(rng.randint(0, 3)):
        ccs.append(
            CreditCard(
                name=f"cc_{i}",
                apr=float(round(rng.uniform(0.0, 0.35), 4)),
                balance=_rng_float(rng, 0, 8000),
                due_day=rng.randint(1, 28),
                min_pct=float(round(rng.uniform(0.01, 0.05), 4)),
                min_floor=_rng_float(rng, 15, 50),
                statement_day=None,
            )
        )

    ious: list[IOU] = []
    for i in range(rng.randint(0, 2)):
        ious.append(
            IOU(
                name=f"iou_{i}",
                balance=_rng_float(rng, 0, 4000),
                apr=float(round(rng.uniform(0.0, 0.25), 4)),
                due_day=rng.choice([None] + list(range(1, 29))),
                min_pct=float(round(rng.uniform(0.0, 0.05), 4)),
                min_floor=_rng_float(rng, 0, 40),
            )
        )

    oneoffs: list[OneOff] = []
    for i in range(rng.randint(0, 4)):
        dd = start + timedelta(days=rng.randint(0, max(1, horizon_days - 1)))
        oneoffs.append(
            OneOff(
                name=f"oneoff_{i}",
                due_date=dd,
                amount=_rng_float(rng, 10, 1500),
                priority=rng.randint(0, 3),
                must_pay=True,
            )
        )

    return Dials(
        current_cash=current_cash,
        safety_cushion=safety_cushion,
        weekday_earnings=weekday_earnings,
        gas_pct=gas_pct,
        gas_fill_size=gas_fill_size,
        bills=bills,
        credit_cards=ccs,
        ious=ious,
        oneoffs=oneoffs,
    )


def generate(*, n: int, seed: int, start: date, horizon_days: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows: list[dict[str, float]] = []

    for _ in range(n):
        d = _mk_dials(rng, start=start, horizon_days=horizon_days)
        df, _metrics = simulate_month(d, start=start, days=horizon_days)

        overdraft = bool((df["balance"] < 0).any())

        feats = featurize_dials(d, start=start, horizon_days=horizon_days)
        feats["label_overdraft"] = 1.0 if overdraft else 0.0

        rows.append(feats)

    out = pd.DataFrame(rows)

    out = out[FEATURE_COLUMNS + ["label_overdraft"]]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic overdraft-risk training data.")
    ap.add_argument("--out", required=True, help="Output Parquet path")
    ap.add_argument("--meta", required=True, help="Output metadata JSON path")

    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--start", type=str, default=None)
    ap.add_argument("--horizon-days", type=int, default=None)

    args = ap.parse_args()

    import yaml

    params = yaml.safe_load(Path("params.yaml").read_text()) if Path("params.yaml").exists() else {}
    rp = params.get("risk", {})

    n = int(args.n if args.n is not None else rp.get("n_samples", 5000))
    seed = int(args.seed if args.seed is not None else rp.get("seed", 1337))
    start = _parse_date(
        args.start if args.start is not None else rp.get("start_date", "2025-01-01")
    )
    horizon_days = int(
        args.horizon_days if args.horizon_days is not None else rp.get("horizon_days", 30)
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta_path = Path(args.meta)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    df = generate(n=n, seed=seed, start=start, horizon_days=horizon_days)
    df.to_parquet(out_path, index=False)

    meta = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "n": n,
        "seed": seed,
        "start": start.isoformat(),
        "horizon_days": horizon_days,
        "features": FEATURE_COLUMNS,
        "label": "label_overdraft",
    }
    meta_path.write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
