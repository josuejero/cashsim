from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol, TypedDict

import pandas as pd

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gx_compat import try_import_great_expectations

gx, _GX_IMPORT_ERROR = try_import_great_expectations()


SUITES = {
    "bills.csv": "cashsim.bills.v1",
    "credit_cards.csv": "cashsim.credit_cards.v1",
    "ious.csv": "cashsim.ious.v1",
    "oneoffs.csv": "cashsim.oneoffs.v1",
    "transactions.csv": "cashsim.transactions.v1",
}


class _FallbackRules(TypedDict):
    columns: list[str]
    required_non_null: set[str]
    ranges: dict[str, tuple[float | None, float | None]]


class _SuiteContext(Protocol):
    def add_or_update_expectation_suite(self, *, expectation_suite: object) -> object: ...


_FALLBACK_RULES: dict[str, _FallbackRules] = {
    "bills.csv": {
        "columns": ["name", "amount", "usual_day", "priority", "must_pay"],
        "required_non_null": {"name"},
        "ranges": {
            "amount": (0.01, None),
            "usual_day": (1, 31),
            "priority": (0, 1000),
        },
    },
    "credit_cards.csv": {
        "columns": ["name", "balance", "apr", "due_day", "min_pct", "min_floor"],
        "required_non_null": {"name"},
        "ranges": {
            "balance": (0, None),
            "apr": (0, 1),
            "min_pct": (0, 1),
            "min_floor": (0, None),
        },
    },
    "ious.csv": {
        "columns": ["name", "balance", "apr", "due_day", "min_pct", "min_floor"],
        "required_non_null": {"name"},
        "ranges": {
            "balance": (0, None),
            "apr": (0, 1),
            "min_pct": (0, 1),
            "min_floor": (0, None),
        },
    },
    "oneoffs.csv": {
        "columns": ["name", "due_date", "amount", "priority", "must_pay"],
        "required_non_null": {"name", "due_date"},
        "ranges": {
            "amount": (0.01, None),
            "priority": (0, 1000),
        },
    },
    "transactions.csv": {
        "columns": ["date", "name", "amount", "category", "notes"],
        "required_non_null": {"date", "name"},
        "ranges": {
            "amount": (-1e12, 1e12),
        },
    },
}


def _ensure_expectation_suites(context: _SuiteContext) -> bool:
    from scripts.gx_suites import build_suites

    try:
        suites = build_suites()
    except Exception as exc:
        print(f"Great Expectations suites unavailable; using fallback validator. Details: {exc}")
        return False
    for suite in suites:
        try:
            context.add_or_update_expectation_suite(expectation_suite=suite)
        except Exception as exc:
            print(
                f"Great Expectations suite setup failed; using fallback validator. Details: {exc}"
            )
            return False
    return True


def _read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _validate_columns(df: pd.DataFrame, expected: list[str], *, table_name: str) -> bool:
    if list(df.columns) == expected:
        return True
    print(f"{table_name}: expected columns {expected}, got {list(df.columns)}")
    return False


def _validate_non_null(df: pd.DataFrame, column: str, *, table_name: str) -> bool:
    if column not in df.columns:
        print(f"{table_name}: missing required column {column}")
        return False
    if df[column].isna().any():
        print(f"{table_name}: null values in column {column}")
        return False
    return True


def _validate_range(
    df: pd.DataFrame,
    column: str,
    *,
    min_value: float | None,
    max_value: float | None,
    table_name: str,
) -> bool:
    if column not in df.columns:
        print(f"{table_name}: missing numeric column {column}")
        return False
    original_na = df[column].isna()
    series = pd.to_numeric(df[column], errors="coerce")
    non_numeric = series.isna() & ~original_na
    if non_numeric.any():
        print(f"{table_name}: non-numeric values in column {column}")
        return False
    if min_value is not None and (series[~original_na] < min_value).any():
        print(f"{table_name}: values below {min_value} in column {column}")
        return False
    if max_value is not None and (series[~original_na] > max_value).any():
        print(f"{table_name}: values above {max_value} in column {column}")
        return False
    return True


def _validate_table_fallback(
    df: pd.DataFrame,
    *,
    table_name: str,
    columns: list[str],
    required_non_null: set[str],
    ranges: dict[str, tuple[float | None, float | None]],
) -> bool:
    ok = _validate_columns(df, columns, table_name=table_name)
    for column in sorted(required_non_null):
        ok = _validate_non_null(df, column, table_name=table_name) and ok
    for column, (min_value, max_value) in ranges.items():
        ok = (
            _validate_range(
                df, column, min_value=min_value, max_value=max_value, table_name=table_name
            )
            and ok
        )
    return ok


def _validate_inputs_fallback(inputs_dir: Path) -> bool:
    all_ok = True
    for filename, rules in _FALLBACK_RULES.items():
        csv_path = inputs_dir / filename
        df = _read_csv_if_exists(csv_path)
        if df is None:
            if filename in {"transactions.csv"}:
                continue
            all_ok = False
            print(f"Missing required file: {csv_path}")
            continue

        ok = _validate_table_fallback(df, table_name=filename, **rules)
        all_ok = all_ok and ok
    return all_ok


def validate_inputs(inputs_dir: Path) -> bool:
    if gx is None:
        if _GX_IMPORT_ERROR is not None:
            print(
                "Great Expectations unavailable; using fallback validator. "
                f"Details: {_GX_IMPORT_ERROR}"
            )
        return _validate_inputs_fallback(inputs_dir)

    repo_root = Path(__file__).resolve().parents[1]
    context = gx.get_context(project_root_dir=repo_root, mode="file")

    if not _ensure_expectation_suites(context):
        return _validate_inputs_fallback(inputs_dir)

    ds = context.sources.add_or_update_pandas(name="cashsim_inputs")

    all_ok = True

    for filename, suite_name in SUITES.items():
        csv_path = inputs_dir / filename
        df = _read_csv_if_exists(csv_path)
        if df is None:
            # Optional files are ok to skip
            if filename in {"transactions.csv"}:
                continue
            all_ok = False
            print(f"Missing required file: {csv_path}")
            continue

        asset_name = filename.replace(".csv", "")
        try:
            asset = ds.get_asset(asset_name)
        except Exception:
            asset = ds.add_dataframe_asset(name=asset_name)

        batch_request = asset.build_batch_request(dataframe=df)
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name,
        )
        results = validator.validate()
        if not results.success:
            all_ok = False

    # Build Data Docs (includes latest validation results)
    try:
        context.build_data_docs()
    except Exception as e:
        print(f"Data Docs build failed: {e}")

    return all_ok


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--inputs", required=True)
    args = p.parse_args()

    ok = validate_inputs(Path(args.inputs))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
