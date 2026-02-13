from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LedgerEntry(BaseModel):
    date: date
    name: str
    delta: float
    balance: float


class MonthSummary(BaseModel):
    month: int = Field(ge=1, le=12)
    year: int
    net: float
    balance: float
    is_partial: bool
    covered_start: date
    covered_end: date


class PayPeriodSummary(BaseModel):
    start_date: date
    end_date: date
    is_partial: bool
    spent: float
    net: float
    start_balance: float
    end_balance: float
    min_balance: float


class ProjectionResponse(BaseModel):
    as_of: date
    from_date: date
    current_balance: float
    ledger: list[LedgerEntry]
    months: list[MonthSummary]
    pay_periods: list[PayPeriodSummary]
