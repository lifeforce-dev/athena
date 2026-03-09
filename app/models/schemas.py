from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LedgerEntry(BaseModel):
    date: date
    name: str
    delta: Decimal
    balance: Decimal


class MonthSummary(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int
    net: Decimal
    balance: Decimal
    is_partial: bool
    covered_start: date
    covered_end: date


class PayPeriodSummary(BaseModel):
    start_date: date
    end_date: date
    is_partial: bool
    spent: Decimal
    net: Decimal
    start_balance: Decimal
    end_balance: Decimal
    min_balance: Decimal


class ProjectionResponse(BaseModel):
    as_of: date
    from_date: date
    current_balance: Decimal
    has_initial_balance: bool
    ledger: list[LedgerEntry]
    months: list[MonthSummary]
    pay_periods: list[PayPeriodSummary]

    # Risk analysis — computed via expenses-before-income walk.
    lowest_balance: Decimal = Decimal(0)
    lowest_date: date | None = None
    risk_level: str = "comfortable"
    cushion_ratio: Decimal = Decimal(1)
    total_outflows: Decimal = Decimal(0)
    total_inflows: Decimal = Decimal(0)
    goes_negative: bool = False
    negative_date: date | None = None
    negative_balance: Decimal | None = None
    days_until_negative: int | None = None
    drain_rate: Decimal = Decimal(0)
    lowest_ratio: Decimal = Decimal(1)


class ScenarioRequest(BaseModel):
    """Request body for running a what-if scenario projection."""

    as_of: date
    from_date: date | None = None
    excluded_ids: list[int] = Field(default_factory=list)
    amount_overrides: dict[int, Decimal] = Field(default_factory=dict)
