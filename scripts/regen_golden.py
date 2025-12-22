from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from cashsim.batch import run_from_config
from cashsim.io.exporters import write_metrics_json, write_series_csv


def _scenario_name(config_path: Path) -> str:
    stem = config_path.stem
    return stem.replace(".", "_")


def main() -> None:
    ap = argparse.ArgumentParser(description="Regenerate CashSim golden fixtures.")
    ap.add_argument("--start", default="2025-01-01", help="YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=31)
    ap.add_argument("--src", type=Path, default=Path("examples/configs"))
    ap.add_argument("--out", type=Path, default=Path("tests/fixtures/golden"))
    ap.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help=(
            "Optional list of config basenames (without .json) to include. "
            "Example: debt_payoff stress_tight.fixed"
        ),
    )
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    start = date.fromisoformat(args.start)

    if not args.src.exists():
        raise SystemExit(f"Source dir not found: {args.src}")

    configs = sorted(args.src.glob("*.json"))
    if args.scenarios:
        wanted = set(args.scenarios)
        configs = [p for p in configs if p.stem in wanted]

    if not configs:
        raise SystemExit("No configs found. Check --src or --scenarios.")

    args.out.mkdir(parents=True, exist_ok=True)

    meta = {
        "start": args.start,
        "days": args.days,
        "source_dir": str(args.src),
        "scenarios": [_scenario_name(p) for p in configs],
    }
    (args.out / "_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for cfg in configs:
        name = _scenario_name(cfg)
        dest = args.out / name

        if dest.exists() and not args.overwrite:
            raise SystemExit(f"Refusing to overwrite {dest} (use --overwrite)")

        dest.mkdir(parents=True, exist_ok=True)

        config_copy = dest / "config.json"
        shutil.copyfile(cfg, config_copy)

        run = run_from_config(config=config_copy, start=start, days=args.days)
        write_metrics_json(run.metrics, dest / "metrics.json")
        write_series_csv(run.df, dest / "series.csv")

        print(f"Wrote golden scenario: {name} -> {dest}")


if __name__ == "__main__":
    main()
