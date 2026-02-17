"""Tests for commitment_repository domain model conversion.

Validates that flat DB columns (frequency, anchor_date, day_of_month, etc.)
are correctly converted into discriminated Recurrence union types used by
the projection engine.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.domain import (
    DayInterval,
    Direction,
    MonthDay,
    OneTime,
    TemplateTag,
    WeekdayCadence,
)
from app.repositories.commitment_repository import to_domain

# Access the private function through the module for testing.
import app.repositories.commitment_repository as _repo
_build_recurrence = _repo._build_recurrence  # type: ignore[attr-defined]


def _make_commitment(**overrides: object) -> MagicMock:
    """Build a minimal mock Commitment ORM row with sensible defaults."""
    defaults = {
        "id": 1,
        "user_id": 1,
        "name": "Test",
        "amount": Decimal("-100.00"),
        "frequency": "monthly",
        "day_of_month": 15,
        "anchor_date": None,
        "one_time_date": None,
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "is_paycheck": False,
    }
    defaults.update(overrides)
    row = MagicMock()
    for key, value in defaults.items():
        setattr(row, key, value)
    return row


# -- _build_recurrence -----------------------------------------------------


class TestBuildRecurrence:
    def test_daily(self):
        row = _make_commitment(
            frequency="daily",
            anchor_date=date(2026, 3, 1),
        )
        result = _build_recurrence(row)

        assert isinstance(result, DayInterval)
        assert result.interval_days == 1
        assert result.anchor_date == date(2026, 3, 1)

    def test_daily_falls_back_to_start_date(self):
        row = _make_commitment(
            frequency="daily",
            anchor_date=None,
            start_date=date(2026, 5, 10),
        )
        result = _build_recurrence(row)

        assert isinstance(result, DayInterval)
        assert result.anchor_date == date(2026, 5, 10)

    def test_weekly(self):
        # 2026-01-05 is a Monday (weekday=0).
        row = _make_commitment(
            frequency="weekly",
            anchor_date=date(2026, 1, 5),
        )
        result = _build_recurrence(row)

        assert isinstance(result, WeekdayCadence)
        assert result.interval_weeks == 1
        assert result.weekday == 0  # Monday

    def test_biweekly(self):
        # 2026-01-09 is a Friday (weekday=4).
        row = _make_commitment(
            frequency="biweekly",
            anchor_date=date(2026, 1, 9),
        )
        result = _build_recurrence(row)

        assert isinstance(result, WeekdayCadence)
        assert result.interval_weeks == 2
        assert result.weekday == 4  # Friday

    def test_monthly(self):
        row = _make_commitment(frequency="monthly", day_of_month=28)
        result = _build_recurrence(row)

        assert isinstance(result, MonthDay)
        assert result.day_of_month == 28

    def test_monthly_falls_back_to_start_date_day(self):
        row = _make_commitment(
            frequency="monthly",
            day_of_month=None,
            start_date=date(2026, 4, 20),
        )
        result = _build_recurrence(row)

        assert isinstance(result, MonthDay)
        assert result.day_of_month == 20

    def test_once(self):
        row = _make_commitment(frequency="once")
        result = _build_recurrence(row)
        assert isinstance(result, OneTime)

    def test_unknown_frequency_treated_as_one_time(self):
        row = _make_commitment(frequency="quarterly")
        result = _build_recurrence(row)
        assert isinstance(result, OneTime)


# -- to_domain -------------------------------------------------------------


class TestToDomain:
    def test_positive_amount_is_inflow(self):
        row = _make_commitment(amount=Decimal("3000.00"))
        template = to_domain(row)

        assert template.direction == Direction.INFLOW
        assert template.amount == Decimal("3000.00")

    def test_negative_amount_is_outflow(self):
        row = _make_commitment(amount=Decimal("-1200.00"))
        template = to_domain(row)

        assert template.direction == Direction.OUTFLOW
        assert template.amount == Decimal("1200.00")

    def test_paycheck_flag_adds_tag(self):
        row = _make_commitment(is_paycheck=True, amount=Decimal("2000.00"))
        template = to_domain(row)

        assert TemplateTag.PAYCHECK in template.tags

    def test_non_paycheck_has_no_tags(self):
        row = _make_commitment(is_paycheck=False)
        template = to_domain(row)

        assert template.tags == []

    def test_once_prefers_one_time_date(self):
        row = _make_commitment(
            frequency="once",
            one_time_date=date(2026, 7, 4),
            start_date=date(2026, 1, 1),
        )
        template = to_domain(row)

        assert template.start_date == date(2026, 7, 4)

    def test_once_falls_back_to_start_date(self):
        row = _make_commitment(
            frequency="once",
            one_time_date=None,
            start_date=date(2026, 1, 1),
        )
        template = to_domain(row)

        assert template.start_date == date(2026, 1, 1)

    def test_end_date_passed_through(self):
        row = _make_commitment(end_date=date(2026, 12, 31))
        template = to_domain(row)

        assert template.end_date == date(2026, 12, 31)

    def test_name_preserved(self):
        row = _make_commitment(name="Monthly Rent")
        template = to_domain(row)

        assert template.name == "Monthly Rent"

    def test_monthly_recurrence_in_full_conversion(self):
        row = _make_commitment(frequency="monthly", day_of_month=5)
        template = to_domain(row)

        assert isinstance(template.recurrence, MonthDay)
        assert template.recurrence.day_of_month == 5
