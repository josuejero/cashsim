from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from cashsim.models import Dials

SCHEMA_VERSION = "v1"

FILES_V1 = {
    "manifest": "manifest.json",
    "dials": "dials.json",
    "bills": "bills.csv",
    "credit_cards": "credit_cards.csv",
    "ious": "ious.csv",
    "oneoffs": "oneoffs.csv",
    "transactions": "transactions.csv",
}

BILLS_COLS = ["name", "amount", "usual_day", "priority", "must_pay"]
CARDS_COLS = ["name", "balance", "apr", "due_day", "min_pct", "min_floor"]
ONEOFFS_COLS = ["name", "due_date", "amount", "priority", "must_pay"]
TXNS_COLS = ["date", "name", "amount", "category", "notes"]


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_input_tables(
    dials: Dials,
    out_dir: Path,
    *,
    schema_version: str = SCHEMA_VERSION,
    overwrite: bool = False,
    include_empty_transactions: bool = True,
) -> Path:
    """Export canonical input tables (v1) into a folder.

    Returns the output directory.
    """

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / FILES_V1["manifest"]
    if manifest_path.exists() and not overwrite:
        raise FileExistsError(f"{manifest_path} exists. Re-run with --overwrite.")

    base = dials.model_dump(mode="json")
    for k in ("bills", "credit_cards", "ious", "oneoffs"):
        base.pop(k, None)
    _write_json(out_dir / FILES_V1["dials"], base)

    bills_df = pd.DataFrame([b.model_dump(mode="json") for b in dials.bills])
    if not bills_df.empty:
        bills_df = bills_df.reindex(columns=BILLS_COLS)
    bills_df.to_csv(out_dir / FILES_V1["bills"], index=False)

    cards_df = pd.DataFrame([c.model_dump(mode="json") for c in dials.credit_cards])
    if not cards_df.empty:
        cards_df = cards_df.reindex(columns=CARDS_COLS)
        cards_df["due_day"] = cards_df["due_day"].astype("Int64")
    cards_df.to_csv(out_dir / FILES_V1["credit_cards"], index=False, na_rep="")

    ious_df = pd.DataFrame([i.model_dump(mode="json") for i in dials.ious])
    if not ious_df.empty:
        ious_df = ious_df.reindex(columns=CARDS_COLS)
        ious_df["due_day"] = ious_df["due_day"].astype("Int64")
    ious_df.to_csv(out_dir / FILES_V1["ious"], index=False, na_rep="")

    oneoffs_df = pd.DataFrame([o.model_dump(mode="json") for o in dials.oneoffs])
    if not oneoffs_df.empty:
        oneoffs_df = oneoffs_df.reindex(columns=ONEOFFS_COLS)
    oneoffs_df.to_csv(out_dir / FILES_V1["oneoffs"], index=False)

    if include_empty_transactions:
        txns_path = out_dir / FILES_V1["transactions"]
        if not txns_path.exists() or overwrite:
            pd.DataFrame(columns=TXNS_COLS).to_csv(txns_path, index=False)

    manifest = {
        "schema_version": schema_version,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "files": {
            "dials": FILES_V1["dials"],
            "bills": FILES_V1["bills"],
            "credit_cards": FILES_V1["credit_cards"],
            "ious": FILES_V1["ious"],
            "oneoffs": FILES_V1["oneoffs"],
            "transactions": FILES_V1["transactions"],
        },
    }
    _write_json(manifest_path, manifest)

    return out_dir
