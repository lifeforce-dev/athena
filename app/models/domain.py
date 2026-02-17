from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Discriminator, Field, Tag, field_validator

# ---------------------------
# Date helpers
# ---------------------------


def ensure_date(value: Any) -> date:
    """Parse a value into a date, supporting multiple string formats."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Could not parse date from {value!r}")


def ensure_optional_date(value: Any) -> date | None:
    """Parse a value into an optional date (None-safe)."""
    if value in (None, "", 0):
        return None
    return ensure_date(value)


# ---------------------------
# Recurrence types
# ---------------------------


class Direction(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class TemplateTag(StrEnum):
    """Validated tags that can be applied to cash-flow templates."""

    PAYCHECK = "paycheck"


class RecurrenceType(StrEnum):
    WEEKDAY_CADENCE = "weekday_cadence"
    DAY_INTERVAL = "day_interval"
    MONTH_DAY = "month_day"
    ONE_TIME = "one_time"


class WeekdayCadence(BaseModel):
    type: Literal["weekday_cadence"] = "weekday_cadence"
    interval_weeks: int = Field(gt=0)
    weekday: int = Field(ge=0, le=6)  # Monday=0 .. Sunday=6
    anchor_date: date

    @field_validator("anchor_date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date:
        return ensure_date(v)


class DayInterval(BaseModel):
    type: Literal["day_interval"] = "day_interval"
    interval_days: int = Field(gt=0)
    anchor_date: date

    @field_validator("anchor_date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date:
        return ensure_date(v)


class MonthDay(BaseModel):
    type: Literal["month_day"] = "month_day"
    day_of_month: int = Field(ge=1, le=31)
    anchor_date: date | None = None

    @field_validator("anchor_date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date | None:
        return ensure_optional_date(v)


class OneTime(BaseModel):
    type: Literal["one_time"] = "one_time"


Recurrence = Annotated[
    Annotated[WeekdayCadence, Tag("weekday_cadence")]
    | Annotated[DayInterval, Tag("day_interval")]
    | Annotated[MonthDay, Tag("month_day")]
    | Annotated[OneTime, Tag("one_time")],
    Discriminator("type"),
]


# ---------------------------
# Cash-flow template
# ---------------------------


class CashFlowTemplate(BaseModel):
    name: str
    amount: Decimal = Field(gt=0)
    direction: Direction
    recurrence: Recurrence
    start_date: date
    end_date: date | None = None
    tags: list[TemplateTag] = Field(default_factory=list)

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, v: Any) -> date:
        return ensure_date(v)

    @field_validator("end_date", mode="before")
    @classmethod
    def parse_end_date(cls, v: Any) -> date | None:
        return ensure_optional_date(v)

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.direction == Direction.INFLOW else -self.amount


# ---------------------------
# Top-level config
# ---------------------------


class CashFlowConfig(BaseModel):
    initial_balance: Decimal = Decimal(0)
    templates: list[CashFlowTemplate] = Field(default_factory=list)

    @classmethod
    def from_json(cls, payload: str) -> CashFlowConfig:
        """Parse a JSON string into a CashFlowConfig."""
        return cls.model_validate(json.loads(payload))
