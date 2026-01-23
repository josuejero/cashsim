from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    FAIL = "FAIL"


class ThresholdDirection(str, Enum):
    GT = "gt"
    LT = "lt"


class RuleThreshold(BaseModel):
    warn: float | None = Field(default=None, ge=0)
    fail: float | None = Field(default=None, ge=0)
    comparison: ThresholdDirection = ThresholdDirection.GT

    def severity(self, value: float) -> Severity:
        if self.comparison == ThresholdDirection.GT:
            if self.fail is not None and value > self.fail:
                return Severity.FAIL
            if self.warn is not None and value > self.warn:
                return Severity.WARN
        else:
            if self.fail is not None and value < self.fail:
                return Severity.FAIL
            if self.warn is not None and value < self.warn:
                return Severity.WARN
        return Severity.INFO


class MissingnessRule(BaseModel):
    column: str
    thresholds: RuleThreshold | None = None
    label: str | None = None


class KeyRule(BaseModel):
    columns: list[str]
    name: str | None = None
    kind: Literal["primary", "natural", "aux"] = "natural"
    thresholds: RuleThreshold | None = None

    @field_validator("columns")
    @classmethod
    def _must_have_columns(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Key must declare at least one column")
        return value


class RangeRule(BaseModel):
    column: str
    min_value: float | None = None
    max_value: float | None = None
    thresholds: RuleThreshold | None = None
    label: str | None = None


class AllowedValuesRule(BaseModel):
    column: str
    values: list[str]
    case_sensitive: bool = False
    thresholds: RuleThreshold | None = None
    label: str | None = None

    @field_validator("values")
    @classmethod
    def _non_empty_values(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Allowed values rule must list at least one allowed value")
        return value


class DateRule(BaseModel):
    column: str
    allow_future: bool = False
    order_with: str | None = None
    order: Literal["lte", "lt", "gte", "gt"] = "lte"
    thresholds: RuleThreshold | None = None
    label: str | None = None


class ForeignKeyRule(BaseModel):
    child_table: str
    parent_table: str
    child_columns: list[str]
    parent_columns: list[str]
    allow_unknown: bool = False
    unknown_values: list[str] = []
    thresholds: RuleThreshold | None = None
    name: str | None = None
    label: str | None = None

    @field_validator("child_columns", "parent_columns")
    @classmethod
    def _columns_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Foreign key must reference at least one column")
        return value


class TableConfig(BaseModel):
    name: str
    file: str
    owner: str | None = None
    filter_column: str | None = None
    keys: list[KeyRule] = []
    critical_columns: list[str] = []
    missingness: list[MissingnessRule] = []
    range_rules: list[RangeRule] = []
    allowed_values: list[AllowedValuesRule] = []
    date_rules: list[DateRule] = []
    dedupe_top: int = 5

    @field_validator("dedupe_top")
    @classmethod
    def _positive_dedupe(cls, value: int) -> int:
        if value < 1 or value > 50:
            raise ValueError("dedupe_top must be between 1 and 50")
        return value


class DQThresholds(BaseModel):
    missing: RuleThreshold = RuleThreshold(warn=0.005, fail=0.02, comparison=ThresholdDirection.GT)
    duplicate: RuleThreshold = RuleThreshold(
        warn=0.001, fail=0.01, comparison=ThresholdDirection.GT
    )
    invalid: RuleThreshold = RuleThreshold(warn=0.005, fail=0.02, comparison=ThresholdDirection.GT)
    coverage: RuleThreshold = RuleThreshold(
        warn=0.99,
        fail=0.95,
        comparison=ThresholdDirection.LT,
    )


class DQConfig(BaseModel):
    dataset_name: str
    dataset_root: str | None = None
    dataset_owner: str | None = None
    data_dictionary_link: str = "docs/data_dictionary.md"
    thresholds: DQThresholds = DQThresholds()
    tables: list[TableConfig]
    foreign_keys: list[ForeignKeyRule] = []
    issue_owner: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> tuple[DQConfig, Path]:
        resolved = Path(path)
        data = resolved.read_text(encoding="utf-8")
        config = cls.model_validate_json(data)
        base = resolved.parent
        dataset_root = config.dataset_root
        dataset_dir = base if dataset_root is None else (base / dataset_root).resolve()
        return config, dataset_dir
