from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.gx_compat import try_import_great_expectations

gx, _GX_IMPORT_ERROR = try_import_great_expectations()

if TYPE_CHECKING:
    from great_expectations.core.expectation_configuration import (
        ExpectationConfiguration as _ExpectationConfigurationT,
    )
    from great_expectations.core.expectation_suite import (
        ExpectationSuite as _ExpectationSuiteT,
    )

    type ExpectationConfigurationT = _ExpectationConfigurationT
    type ExpectationSuiteT = _ExpectationSuiteT
else:
    type ExpectationConfigurationT = Any
    type ExpectationSuiteT = Any

ExpectationSuiteClass: type[Any] | None = None
ExpectationConfigurationClass: type[Any] | None = None
if gx is not None:
    try:
        from great_expectations.core.expectation_configuration import (
            ExpectationConfiguration as _ExpectationConfiguration,
        )
        from great_expectations.core.expectation_suite import ExpectationSuite as _ExpectationSuite
    except Exception:
        _ExpectationSuite = None
        _ExpectationConfiguration = None
    ExpectationSuiteClass = _ExpectationSuite
    ExpectationConfigurationClass = _ExpectationConfiguration


def _expectation_suite_class() -> type[Any]:
    if ExpectationSuiteClass is None:
        raise RuntimeError("Great Expectations expectation suites unavailable.")
    return ExpectationSuiteClass


def _expectation_configuration_class() -> type[Any]:
    if ExpectationConfigurationClass is None:
        raise RuntimeError("Great Expectations expectation configuration unavailable.")
    return ExpectationConfigurationClass


def _add_expectation(suite: ExpectationSuiteT, expectation_type: str, **kwargs: object) -> None:
    config_class = _expectation_configuration_class()
    suite.add_expectation(config_class(expectation_type=expectation_type, kwargs=kwargs))


def _suite_bills() -> ExpectationSuiteT:
    suite_class = _expectation_suite_class()
    suite = suite_class(expectation_suite_name="cashsim.bills.v1")
    _add_expectation(
        suite,
        "expect_table_columns_to_match_ordered_list",
        column_list=["name", "amount", "usual_day", "priority", "must_pay"],
    )
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="name")
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="amount",
        min_value=0.01,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="usual_day",
        min_value=1,
        max_value=31,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="priority",
        min_value=0,
        max_value=1000,
    )
    return suite


def _suite_cards(name: str) -> ExpectationSuiteT:
    suite_class = _expectation_suite_class()
    suite = suite_class(expectation_suite_name=name)
    _add_expectation(
        suite,
        "expect_table_columns_to_match_ordered_list",
        column_list=["name", "balance", "apr", "due_day", "min_pct", "min_floor"],
    )
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="name")
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="balance",
        min_value=0,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="apr",
        min_value=0,
        max_value=1,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="min_pct",
        min_value=0,
        max_value=1,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="min_floor",
        min_value=0,
    )
    # due_day may be null
    return suite


def _suite_oneoffs() -> ExpectationSuiteT:
    suite_class = _expectation_suite_class()
    suite = suite_class(expectation_suite_name="cashsim.oneoffs.v1")
    _add_expectation(
        suite,
        "expect_table_columns_to_match_ordered_list",
        column_list=["name", "due_date", "amount", "priority", "must_pay"],
    )
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="name")
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="due_date")
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="amount",
        min_value=0.01,
    )
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="priority",
        min_value=0,
        max_value=1000,
    )
    return suite


def _suite_txns() -> ExpectationSuiteT:
    suite_class = _expectation_suite_class()
    suite = suite_class(expectation_suite_name="cashsim.transactions.v1")
    _add_expectation(
        suite,
        "expect_table_columns_to_match_ordered_list",
        column_list=["date", "name", "amount", "category", "notes"],
    )
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="date")
    _add_expectation(suite, "expect_column_values_to_not_be_null", column="name")
    _add_expectation(
        suite,
        "expect_column_values_to_be_between",
        column="amount",
        min_value=-1e12,
        max_value=1e12,
    )
    return suite


def main() -> None:
    if gx is None:
        print(f"Great Expectations failed to import. Details: {_GX_IMPORT_ERROR}")
        return
    if ExpectationSuiteClass is None:
        print(
            "Great Expectations expectation suites unavailable. "
            "Verify the Great Expectations install."
        )
        return
    if ExpectationConfigurationClass is None:
        print(
            "Great Expectations expectation configuration unavailable. "
            "Verify the Great Expectations install."
        )
        return

    repo_root = Path(__file__).resolve().parents[1]
    context = gx.get_context(project_root_dir=repo_root, mode="file")

    suites = build_suites()

    for s in suites:
        context.add_or_update_expectation_suite(expectation_suite=s)


def build_suites() -> list[ExpectationSuiteT]:
    return [
        _suite_bills(),
        _suite_cards("cashsim.credit_cards.v1"),
        _suite_cards("cashsim.ious.v1"),
        _suite_oneoffs(),
        _suite_txns(),
    ]


if __name__ == "__main__":
    main()
