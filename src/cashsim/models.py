from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Bill(BaseModel):
    name: str = Field(min_length=1)
    usual_day: int = Field(ge=1, le=31)
    amount: float = Field(ge=0)

    @field_validator("amount")
    @classmethod
    def two_decimals(cls, v: float) -> float:
        return round(float(v), 2)


class CreditCard(BaseModel):
    name: str = Field(min_length=1)
    apr: float = Field(ge=0, description="APR as decimal, e.g. 0.2499 for 24.99%")
    balance: float = Field(ge=0)
    due_day: int = Field(ge=1, le=31, description="Payment due day")
    min_pct: float = Field(ge=0, le=1, description="e.g. 0.02 for 2%")
    min_floor: float = Field(ge=0, description="absolute floor, e.g. $25")
    statement_day: int | None = Field(
        default=None,
        ge=1,
        le=31,
        description="If None, we approximate as due_day-21 (CARD Act minimum).",
    )


class IOU(BaseModel):
    name: str = Field(min_length=1)
    balance: float = Field(ge=0)
    apr: float = Field(ge=0, description="APR decimal; 0.0 if no interest")
    due_day: int | None = Field(default=None, ge=1, le=31)
    min_pct: float = Field(default=0.0, ge=0, le=1)
    min_floor: float = Field(default=0.0, ge=0)


class OneOff(BaseModel):
    name: str = Field(min_length=1)
    due_date: date
    amount: float = Field(ge=0)
    priority: int = 0
    must_pay: bool = True

    @field_validator("amount")
    @classmethod
    def two_decimals(cls, v: float) -> float:
        return round(float(v), 2)


class InvestmentSettings(BaseModel):
    enable: bool = True
    hysa_apy: float = Field(ge=0, default=0.045)
    expected_market_return: float = Field(ge=0, default=0.07)
    use_dca: bool = True
    roth_target: float = Field(ge=0, default=0.0)
    trad_target: float = Field(ge=0, default=0.0)
    hysa_target: float = Field(ge=0, default=0.0)
    robinhood_target: float = Field(ge=0, default=0.0)
    ira_year_limit: float = Field(ge=0, default=7000.0)
    roth_ok_today: bool = True


class Dials(BaseModel):
    current_cash: float = Field(ge=0)
    safety_cushion: float = Field(ge=0)
    weekday_earnings: float = Field(ge=0, description="Treated as DAILY earnings (7d/wk)")
    gas_pct: float = Field(ge=0, le=1)
    gas_fill_size: float = Field(gt=0)
    bills: list[Bill]
    credit_cards: list[CreditCard] = []
    ious: list[IOU] = []
    oneoffs: list[OneOff] = []
    invest: InvestmentSettings = InvestmentSettings()
    interest_mode: Literal["statement_adb", "due_simple"] = "statement_adb"
    extra_strategy: Literal["avalanche", "snowball"] = "avalanche"

    blackouts: list[date] = []
