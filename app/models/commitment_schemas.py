"""Pydantic models for commitment API requests and responses."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


FrequencyLiteral = Literal[
    "daily",
    "weekly",
    "biweekly",
    "monthly",
    "day_interval",
    "once",
]


class CommitmentCreate(BaseModel):
    """Request body for creating a commitment."""

    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(description="Signed: negative = expense, positive = income.")
    frequency: FrequencyLiteral
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    interval_days: int | None = Field(default=None, ge=1)
    anchor_date: date | None = None
    one_time_date: date | None = None
    start_date: date
    end_date: date | None = None
    is_paycheck: bool = False

    @model_validator(mode="after")
    def validate_frequency_fields(self) -> CommitmentCreate:
        """Ensure the right columns are set for each frequency type."""
        if self.frequency == "monthly" and self.day_of_month is None:
            raise ValueError("day_of_month is required for monthly frequency")

        if self.frequency in ("weekly", "biweekly", "daily") and self.anchor_date is None:
            raise ValueError("anchor_date is required for weekly/biweekly/daily frequency")

        if self.frequency == "day_interval":
            if self.interval_days is None:
                raise ValueError("interval_days is required for day_interval frequency")
            if self.anchor_date is None:
                raise ValueError("anchor_date is required for day_interval frequency")

        if self.frequency == "once" and self.one_time_date is None:
            raise ValueError("one_time_date is required for once frequency")

        return self


class CommitmentUpdate(BaseModel):
    """Request body for updating a commitment. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None)
    frequency: FrequencyLiteral | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    interval_days: int | None = Field(default=None, ge=1)
    anchor_date: date | None = None
    one_time_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_paycheck: bool | None = None


class CommitmentResponse(BaseModel):
    """API response for a single commitment."""

    id: int
    name: str
    amount: Decimal
    frequency: str
    day_of_month: int | None
    interval_days: int | None
    anchor_date: date | None
    one_time_date: date | None
    start_date: date
    end_date: date | None
    is_paycheck: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
