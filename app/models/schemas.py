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
