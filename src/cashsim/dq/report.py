from __future__ import annotations

import csv
import json
import math
from collections import Counter
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from cashsim.dq.config import (
    DQConfig,
    DQThresholds,
    MissingnessRule,
    Severity,
    TableConfig,
)

DEFAULT_OUTPUT_DIR = Path("out/dq-report")
DEFAULT_ISSUE_NAME = "issue_stub.md"


@dataclass
class CheckResult:
    table: str
    check_name: str
    check_type: str
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    owner: str | None = None
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "check_type": self.check_type,
            "check_name": self.check_name,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "owner": self.owner,
            "examples": self.examples,
        }


@dataclass
class ReportResult:
    json_path: Path
    csv_path: Path
    markdown_path: Path | None
    issue_path: Path | None
    severity_summary: dict[Severity, int]
    exit_code: int


def run_data_quality_report(
    config_path: str | Path,
    dataset_root: Path | None = None,
    since: date | None = None,
    output_dir: Path | None = None,
    include_markdown: bool = True,
    max_examples: int = 3,
) -> ReportResult:
    resolved_path = Path(config_path)
    config, inferred_root = DQConfig.load(resolved_path)
    dataset_dir = dataset_root.resolve() if dataset_root is not None else inferred_root
    output_folder = (output_dir or DEFAULT_OUTPUT_DIR).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    table_dfs: dict[str, pd.DataFrame] = {}
    owner_map: dict[str, str] = {}
    for table in config.tables:
        path = (dataset_dir / table.file).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Table {table.name} not found at {path}")
        df = _load_table(path)
        df = _apply_since_filter(df, table, since)
        table_dfs[table.name] = df
        owner_map[table.name] = _resolve_owner(table, config)

    results: list[CheckResult] = []
    for table in config.tables:
        df = table_dfs[table.name]
        results.extend(
            _run_table_checks(
                table=table,
                df=df,
                owner=owner_map.get(table.name),
                thresholds=config.thresholds,
                max_examples=max_examples,
            )
        )

    fk_results = _run_foreign_key_checks(config, table_dfs, owner_map, max_examples)
    results.extend(fk_results)

    severity_summary = {Severity.INFO: 0, Severity.WARN: 0, Severity.FAIL: 0}
    for item in results:
        severity_summary[item.severity] += 1

    json_path = output_folder / "dq_report.json"
    csv_path = output_folder / "dq_report.csv"
    markdown_path = output_folder / "dq_report.md" if include_markdown else None
    issue_stub_path = output_folder / DEFAULT_ISSUE_NAME
    issue_path: Path | None = issue_stub_path

    metadata = {
        "dataset": config.dataset_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "since": since.isoformat() if since is not None else None,
        "tables": [table.name for table in config.tables],
        "config_path": str(resolved_path.resolve()),
        "thresholds": config.thresholds.model_dump(),
    }

    _write_json(metadata, results, json_path)
    _write_csv(results, csv_path)
    if include_markdown and markdown_path is not None:
        _write_markdown(results, metadata, config, markdown_path)

    fail_results = [result for result in results if result.severity == Severity.FAIL]
    if fail_results:
        _write_issue_stub(config, fail_results, issue_stub_path)
    else:
        issue_path = None

    exit_code = 1 if severity_summary[Severity.FAIL] > 0 else 0

    return ReportResult(
        json_path=json_path,
        csv_path=csv_path,
        markdown_path=markdown_path if include_markdown else None,
        issue_path=issue_path,
        severity_summary=severity_summary,
        exit_code=exit_code,
    )


def _load_table(path: Path) -> pd.DataFrame:
    lower_suffix = path.suffix.lower()
    if lower_suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if lower_suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported table format for {path}")


def _apply_since_filter(
    df: pd.DataFrame,
    table: TableConfig,
    since: date | None,
) -> pd.DataFrame:
    if since is None or table.filter_column is None:
        return df
    if table.filter_column not in df.columns:
        return df
    column = pd.to_datetime(df[table.filter_column], errors="coerce")
    mask = column.dt.date >= since
    return df.loc[mask].reset_index(drop=True)


def _resolve_owner(table: TableConfig, config: DQConfig) -> str:
    return table.owner or config.issue_owner or config.dataset_owner or "data-team"


def _run_table_checks(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(_run_missingness(table, df, owner, thresholds, max_examples))
    results.extend(_run_duplicates(table, df, owner, thresholds, max_examples))
    results.extend(_run_range_checks(table, df, owner, thresholds, max_examples))
    results.extend(_run_allowed_values(table, df, owner, thresholds, max_examples))
    results.extend(_run_date_checks(table, df, owner, thresholds, max_examples))
    return results


def _run_missingness(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    rules: list[MissingnessRule] = [MissingnessRule(column=col) for col in table.critical_columns]
    rules.extend(table.missingness)
    total_rows = len(df)
    results: list[CheckResult] = []
    for rule in rules:
        threshold = rule.thresholds or thresholds.missing
        if rule.column not in df.columns:
            results.append(_missing_column_result(table.name, rule.column, owner, "missingness"))
            continue
        series = df[rule.column]
        null_mask = series.isna()
        blank_mask = (~null_mask) & series.astype(str).str.strip().eq("")
        missing_mask = null_mask | blank_mask
        missing_count = int(missing_mask.sum())
        null_count = int(null_mask.sum())
        blank_count = int(blank_mask.sum())
        percent_missing = missing_count / total_rows if total_rows else 0.0
        percent_null = null_count / total_rows if total_rows else 0.0
        percent_blank = blank_count / total_rows if total_rows else 0.0
        severity = threshold.severity(percent_missing)
        message = (
            f"{percent_missing * 100:.2f}% missing in {rule.column}"
            if total_rows
            else f"Column {rule.column} has 0 rows"
        )
        details = {
            "column": rule.column,
            "missing_percent": percent_missing,
            "null_percent": percent_null,
            "blank_percent": percent_blank,
            "missing_count": missing_count,
            "row_count": total_rows,
        }
        examples = _example_rows(df, missing_mask, max_examples)
        results.append(
            CheckResult(
                table=table.name,
                check_type="missingness",
                check_name=f"missingness::{rule.column}",
                severity=severity,
                message=message,
                details=details,
                owner=owner,
                examples=examples,
            )
        )
    return results


def _run_duplicates(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    total_rows = len(df)
    for key in table.keys:
        threshold = key.thresholds or thresholds.duplicate
        missing_columns = [col for col in key.columns if col not in df.columns]
        if missing_columns:
            results.append(
                _missing_column_result(table.name, missing_columns[0], owner, "duplicates")
            )
            continue
        key_counts: Counter[tuple[Any, ...]] = Counter()
        for _, row in df.iterrows():
            key_tuple = tuple(_simplify_value(row[col]) for col in key.columns)
            key_counts[key_tuple] += 1
        duplicate_rows = sum(count - 1 for count in key_counts.values() if count > 1)
        duplicate_rate = duplicate_rows / total_rows if total_rows else 0.0
        severity = threshold.severity(duplicate_rate)
        top_candidates = [
            {"key": list(key), "count": count}
            for key, count in key_counts.most_common(table.dedupe_top)
            if count > 1
        ]
        message = (
            f"{duplicate_rows} duplicate rows ({duplicate_rate * 100:.2f}% )"
            if total_rows
            else "No rows to evaluate duplicates"
        )
        details = {
            "columns": key.columns,
            "duplicate_rows": duplicate_rows,
            "duplicate_rate": duplicate_rate,
            "top_candidates": top_candidates,
        }
        examples: list[dict[str, Any]] = []
        if top_candidates:
            examples.append({"key": top_candidates[0]["key"], "count": top_candidates[0]["count"]})
        results.append(
            CheckResult(
                table=table.name,
                check_type="duplicates",
                check_name=key.name or f"duplicates::{table.name}::{','.join(key.columns)}",
                severity=severity,
                message=message,
                details=details,
                owner=owner,
                examples=examples,
            )
        )
    return results


def _run_range_checks(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    total_rows = len(df)
    for rule in table.range_rules:
        threshold = rule.thresholds or thresholds.invalid
        if rule.column not in df.columns:
            results.append(_missing_column_result(table.name, rule.column, owner, "range"))
            continue
        series = pd.to_numeric(df[rule.column], errors="coerce")
        numeric_mask = series.notna()
        below = pd.Series(False, index=df.index)
        above = pd.Series(False, index=df.index)
        if rule.min_value is not None:
            below = numeric_mask & (series < rule.min_value)
        if rule.max_value is not None:
            above = numeric_mask & (series > rule.max_value)
        non_numeric = (~numeric_mask) & df[rule.column].notna()
        violation_mask = below | above | non_numeric
        violation_count = int(violation_mask.sum())
        violation_rate = violation_count / total_rows if total_rows else 0.0
        severity = threshold.severity(violation_rate)
        range_desc = {
            "min": rule.min_value,
            "max": rule.max_value,
        }
        message = (
            f"{violation_count} rows ({violation_rate * 100:.2f}%) outside range"
            if total_rows
            else "No rows to evaluate ranges"
        )
        details = {
            "column": rule.column,
            "range": range_desc,
            "non_numeric_ratio": float(non_numeric.sum() / total_rows) if total_rows else 0.0,
            "violation_rate": violation_rate,
            "row_count": total_rows,
        }
        examples = _example_rows(df, violation_mask, max_examples)
        results.append(
            CheckResult(
                table=table.name,
                check_type="range",
                check_name=f"range::{rule.column}",
                severity=severity,
                message=message,
                details=details,
                owner=owner,
                examples=examples,
            )
        )
    return results


def _run_allowed_values(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    total_rows = len(df)
    for rule in table.allowed_values:
        threshold = rule.thresholds or thresholds.invalid
        if rule.column not in df.columns:
            results.append(_missing_column_result(table.name, rule.column, owner, "allowed-values"))
            continue
        allowed_set = set(rule.values)
        values = df[rule.column].fillna("")
        normalized = (
            values.astype(str) if rule.case_sensitive else values.astype(str).str.casefold()
        )
        normalized_allowed = (
            allowed_set if rule.case_sensitive else {value.casefold() for value in allowed_set}
        )
        invalid_mask = ~normalized.isin(normalized_allowed)
        invalid_count = int(invalid_mask.sum())
        invalid_rate = invalid_count / total_rows if total_rows else 0.0
        severity = threshold.severity(invalid_rate)
        message = (
            f"{invalid_count} rows ({invalid_rate * 100:.2f}%) with unexpected values"
            if total_rows
            else "No rows to evaluate allowed values"
        )
        details = {
            "column": rule.column,
            "allowed_values": rule.values,
            "invalid_rate": invalid_rate,
            "row_count": total_rows,
        }
        examples = _example_rows(df, invalid_mask, max_examples)
        results.append(
            CheckResult(
                table=table.name,
                check_type="allowed_values",
                check_name=f"allowed_values::{rule.column}",
                severity=severity,
                message=message,
                details=details,
                owner=owner,
                examples=examples,
            )
        )
    return results


def _run_date_checks(
    table: TableConfig,
    df: pd.DataFrame,
    owner: str | None,
    thresholds: DQThresholds,
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    total_rows = len(df)
    today = datetime.now(UTC).date()
    for rule in table.date_rules:
        if rule.column not in df.columns:
            results.append(_missing_column_result(table.name, rule.column, owner, "date"))
            continue
        threshold = rule.thresholds or thresholds.invalid
        series = pd.to_datetime(df[rule.column], errors="coerce")
        rows_with_dates = ~series.isna()
        if not rule.allow_future and total_rows:
            future_mask = rows_with_dates & (series.dt.date > today)
            future_rate = int(future_mask.sum()) / total_rows
            severity = threshold.severity(future_rate)
            message = f"{int(future_mask.sum())} future dates in {rule.column}"
            details = {
                "column": rule.column,
                "future_rate": future_rate,
                "row_count": total_rows,
            }
            examples = _example_rows(df, future_mask, max_examples)
            results.append(
                CheckResult(
                    table=table.name,
                    check_type="date_future",
                    check_name=f"date_future::{rule.column}",
                    severity=severity,
                    message=message,
                    details=details,
                    owner=owner,
                    examples=examples,
                )
            )
        if rule.order_with and rule.order_with in df.columns:
            other = pd.to_datetime(df[rule.order_with], errors="coerce")
            order_mask = pd.Series(False, index=df.index)
            valid_pairs = rows_with_dates & ~other.isna()
            if rule.order == "lte":
                order_mask = valid_pairs & (series > other)
            elif rule.order == "lt":
                order_mask = valid_pairs & (series >= other)
            elif rule.order == "gte":
                order_mask = valid_pairs & (series < other)
            elif rule.order == "gt":
                order_mask = valid_pairs & (series <= other)
            order_rate = int(order_mask.sum()) / total_rows if total_rows else 0.0
            severity = threshold.severity(order_rate)
            message = (
                f"{int(order_mask.sum())} rows violate {rule.order} vs {rule.order_with}"
                if total_rows
                else "No rows to evaluate ordering"
            )
            details = {
                "column": rule.column,
                "order_with": rule.order_with,
                "order": rule.order,
                "order_rate": order_rate,
                "row_count": total_rows,
            }
            examples = _example_rows(df, order_mask, max_examples)
            results.append(
                CheckResult(
                    table=table.name,
                    check_type="date_order",
                    check_name=f"date_order::{rule.column}::{rule.order_with}",
                    severity=severity,
                    message=message,
                    details=details,
                    owner=owner,
                    examples=examples,
                )
            )
    return results


def _run_foreign_key_checks(
    config: DQConfig,
    table_dfs: dict[str, pd.DataFrame],
    owner_map: dict[str, str],
    max_examples: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for rule in config.foreign_keys:
        child_df = table_dfs.get(rule.child_table)
        parent_df = table_dfs.get(rule.parent_table)
        owner = owner_map.get(rule.child_table)
        if child_df is None or parent_df is None:
            missing = rule.child_table if child_df is None else rule.parent_table
            results.append(
                CheckResult(
                    table=missing,
                    check_type="referential",
                    check_name=rule.name or f"fk::{rule.child_table}->{rule.parent_table}",
                    severity=Severity.FAIL,
                    message=f"Missing table data for {missing}",
                    owner=owner,
                )
            )
            continue
        missing_child = [col for col in rule.child_columns if col not in child_df.columns]
        missing_parent = [col for col in rule.parent_columns if col not in parent_df.columns]
        if missing_child or missing_parent:
            missing_col = (missing_child or missing_parent)[0]
            results.append(
                CheckResult(
                    table=rule.child_table,
                    check_type="referential",
                    check_name=rule.name or f"fk::{rule.child_table}->{rule.parent_table}",
                    severity=Severity.FAIL,
                    message=f"Missing column {missing_col} for referential check",
                    owner=owner,
                )
            )
            continue
        parent_keys = {
            tuple(_simplify_value(row[col]) for col in rule.parent_columns)
            for _, row in parent_df.iterrows()
        }
        unknown_set = set(rule.unknown_values)
        orphan_indices: list[Hashable] = []
        filtered_count = 0
        for idx, row in child_df.iterrows():
            child_key = tuple(_simplify_value(row[col]) for col in rule.child_columns)
            if rule.allow_unknown and any(str(value) in unknown_set for value in child_key):
                continue
            if any(value is None for value in child_key):
                orphan_indices.append(idx)
                filtered_count += 1
                continue
            filtered_count += 1
            if child_key not in parent_keys:
                orphan_indices.append(idx)
        orphan_count = len(orphan_indices)
        eligible = filtered_count
        coverage = (eligible - orphan_count) / eligible if eligible else 1.0
        threshold = rule.thresholds or config.thresholds.coverage
        severity = threshold.severity(coverage)
        details = {
            "child_columns": rule.child_columns,
            "parent_columns": rule.parent_columns,
            "orphan_count": orphan_count,
            "eligible_rows": eligible,
            "coverage": coverage,
        }
        message = f"{orphan_count} orphan rows (coverage {coverage * 100:.2f}%)"
        examples = []
        if orphan_indices:
            mask = child_df.index.isin(orphan_indices)
            examples = _example_rows(child_df, mask, max_examples)
        results.append(
            CheckResult(
                table=rule.child_table,
                check_type="referential",
                check_name=rule.name or f"fk::{rule.child_table}->{rule.parent_table}",
                severity=severity,
                message=message,
                details=details,
                owner=owner,
                examples=examples,
            )
        )
    return results


def _missing_column_result(
    table: str, column: str, owner: str | None, check_type: str
) -> CheckResult:
    return CheckResult(
        table=table,
        check_type=check_type,
        check_name=f"{check_type}::{column}",
        severity=Severity.FAIL,
        message=f"Missing column: {column}",
        details={"column": column},
        owner=owner,
    )


def _example_rows(df: pd.DataFrame, mask: Iterable[bool], limit: int) -> list[dict[str, Any]]:
    mask_series = pd.Series(mask, index=df.index)
    examples: list[dict[str, Any]] = []
    for idx in mask_series[mask_series].index[:limit]:
        row = df.loc[idx]
        examples.append({"index": int(idx), "row": _simplify_row(row)})
    return examples


def _simplify_row(row: pd.Series) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column, value in row.items():
        column_key = str(column)
        result[column_key] = _simplify_value(value)
    return result


def _simplify_value(value: object) -> object:
    if isinstance(value, pd.Timestamp | datetime):
        return value.isoformat()
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _write_json(metadata: dict[str, Any], results: list[CheckResult], path: Path) -> None:
    payload = {
        "meta": metadata,
        "results": [result.to_dict() for result in results],
    }
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _write_csv(results: list[CheckResult], path: Path) -> None:
    fieldnames = [
        "table",
        "check_type",
        "check_name",
        "severity",
        "message",
        "details",
        "owner",
        "examples",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "table": result.table,
                    "check_type": result.check_type,
                    "check_name": result.check_name,
                    "severity": result.severity.value,
                    "message": result.message,
                    "details": json.dumps(result.details, ensure_ascii=False),
                    "owner": result.owner,
                    "examples": json.dumps(result.examples, ensure_ascii=False),
                }
            )


def _write_markdown(
    results: list[CheckResult],
    metadata: dict[str, Any],
    config: DQConfig,
    path: Path,
) -> None:
    lines: list[str] = []
    lines.append(f"# Data Quality Report — {config.dataset_name}")
    lines.append(f"*Generated at {metadata['generated_at']}*")
    if metadata.get("since"):
        lines.append(f"*Window start: {metadata['since']}*")
    lines.append("\n## Overview")
    lines.append("|Severity|Count|")
    lines.append("|---|---|")
    counts = _summarize_by_severity(results)
    for severity in (Severity.FAIL, Severity.WARN, Severity.INFO):
        lines.append(f"|{severity.value}|{counts.get(severity, 0)}|")
    lines.append("\n## Tables")
    grouped: dict[str, list[CheckResult]] = {}
    for result in results:
        grouped.setdefault(result.table, []).append(result)
    for table_name, entries in grouped.items():
        lines.append(f"\n### {table_name}")
        lines.append("|Check|Severity|Details|")
        lines.append("|---|---|---|")
        for entry in entries:
            details = _format_details_for_md(entry.details)
            lines.append(f"|{entry.check_name}|{entry.severity.value}|{details}|")
    offenders = _top_offenders(results)
    if offenders:
        lines.append("\n## Top Offenders")
        for offender in offenders:
            lines.append(
                f"- **{offender.table}** `{offender.check_name}` "
                f"({offender.severity.value}): {offender.message}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summarize_by_severity(results: list[CheckResult]) -> dict[Severity, int]:
    summary = {Severity.INFO: 0, Severity.WARN: 0, Severity.FAIL: 0}
    for result in results:
        summary[result.severity] += 1
    return summary


def _format_details_for_md(details: dict[str, Any]) -> str:
    if not details:
        return "-"
    return json.dumps(details, ensure_ascii=False)


def _top_offenders(results: list[CheckResult], limit: int = 5) -> list[CheckResult]:
    priority = {Severity.FAIL: 2, Severity.WARN: 1, Severity.INFO: 0}
    offenders = [result for result in results if result.severity in {Severity.FAIL, Severity.WARN}]
    offenders.sort(key=lambda result: priority.get(result.severity, 0), reverse=True)
    return offenders[:limit]


def _write_issue_stub(config: DQConfig, failures: list[CheckResult], path: Path) -> None:
    lines = _issue_stub_lines(config, failures)
    if not lines:
        return
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _issue_stub_lines(config: DQConfig, failures: list[CheckResult]) -> list[str]:
    header = ["# Data Quality Issues", "The following failures need attention:", ""]
    lines = header[:]
    for result in failures:
        lines.append(f"## {result.table} — {result.check_name}")
        lines.append(f"- **Dataset/Table**: {config.dataset_name}/{result.table}")
        lines.append(f"- **Rule**: {result.check_type}")
        lines.append(f"- **Severity**: {result.severity.value}")
        lines.append(
            f"- **Example**: {json.dumps(result.examples[0]) if result.examples else 'n/a'}"
        )
        lines.append(f"- **Suspected cause**: {_suspected_cause(result)}")
        lines.append(f"- **Owner**: {result.owner or config.issue_owner or 'data-team'}")
        anchor = _data_dictionary_anchor(config, result.table)
        lines.append(f"- **Data Dictionary**: [{result.table}]({anchor})")
        lines.append("")
    return lines


def _suspected_cause(result: CheckResult) -> str:
    if result.check_type == "missingness":
        return "Required field has nulls or blanks that exceed thresholds."
    if result.check_type == "duplicates":
        return "Key columns are not unique; likely caused by missing deduplication."  # noqa: E501
    if result.check_type == "range":
        return "Numeric column holds values outside the allowed range."
    if result.check_type == "allowed_values":
        return "Categorical column contains unexpected labels."
    if result.check_type in {"date_future", "date_order"}:
        return "Date values violate configured sanity rules."
    if result.check_type == "referential":
        return "Child rows refer to missing parent keys."
    return "Confirm this failure in the source dataset."


def _data_dictionary_anchor(config: DQConfig, table: str) -> str:
    slug = table.lower().replace(" ", "-")
    return f"{config.data_dictionary_link}#{slug}"
