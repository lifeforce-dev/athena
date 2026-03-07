"""Tests for post-processing, the projection engine, and the API endpoint.

Covers the shared accumulation logic (month summaries, pay-period grouping)
and the full request/response cycle through FastAPI.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.post_processing import process_ledger
from app.core.projection import project_cash_on
from app.models.domain import (
    CashFlowTemplate,
    Direction,
    MonthDay,
    TemplateTag,
    WeekdayCadence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.INFLOW, recurrence=recurrence, start_date=start, end_date=end)


def _outflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.OUTFLOW, recurrence=recurrence, start_date=start, end_date=end)


# ---------------------------------------------------------------------------
# Domain: tag validation
# ---------------------------------------------------------------------------


class TestTemplateTagValidation:
    def test_valid_tag_accepted(self):
        template = CashFlowTemplate(
            name="Salary",
            amount=3000.0,
            direction=Direction.INFLOW,
            recurrence=MonthDay(day_of_month=15),
            start_date=date(2026, 1, 1),
            tags=[TemplateTag.PAYCHECK],
        )

        assert template.tags == [TemplateTag.PAYCHECK]

    def test_invalid_tag_rejected_by_pydantic(self):
        with pytest.raises(Exception):
            CashFlowTemplate(
                name="Salary",
                amount=3000.0,
                direction=Direction.INFLOW,
                recurrence=MonthDay(day_of_month=15),
                start_date=date(2026, 1, 1),
                tags=["not_a_real_tag"],
            )

    def test_empty_tags_by_default(self):
        template = CashFlowTemplate(
            name="Rent",
            amount=1500.0,
            direction=Direction.OUTFLOW,
            recurrence=MonthDay(day_of_month=1),
            start_date=date(2026, 1, 1),
        )

        assert template.tags == []


# ---------------------------------------------------------------------------
# Post-processing: month summaries
# ---------------------------------------------------------------------------


class TestMonthSummaries:
    def test_single_month_produces_one_summary(self):
        raw_ledger = [
            (date(2026, 1, 5), "Rent", Decimal("-1500")),
            (date(2026, 1, 15), "Paycheck", Decimal("3000")),
        ]

        result = process_ledger(raw_ledger, Decimal("5000"), date(2026, 1, 1), date(2026, 1, 31))

        assert len(result.months) == 1
        assert result.months[0].month == 1
        assert result.months[0].year == 2026
        assert result.months[0].net == Decimal("1500")
        assert result.months[0].is_partial is False

    def test_multiple_months_each_get_summary(self):
        raw_ledger = [
            (date(2026, 1, 15), "Income", Decimal("2000")),
            (date(2026, 2, 15), "Income", Decimal("2000")),
            (date(2026, 3, 15), "Income", Decimal("2000")),
        ]

        result = process_ledger(raw_ledger, Decimal("0"), date(2026, 1, 1), date(2026, 3, 31))

        assert len(result.months) == 3
        assert [m.month for m in result.months] == [1, 2, 3]
        assert all(m.net == Decimal("2000") for m in result.months)

    def test_partial_month_flagged(self):
        raw_ledger = [(date(2026, 2, 15), "Income", Decimal("1000"))]

        result = process_ledger(raw_ledger, Decimal("0"), date(2026, 2, 10), date(2026, 2, 28))

        assert result.months[0].is_partial is True
        assert result.months[0].covered_start == date(2026, 2, 10)


# ---------------------------------------------------------------------------
# Post-processing: pay-period grouping
# ---------------------------------------------------------------------------


class TestPayPeriodGrouping:
    def test_paycheck_entries_create_pay_periods(self):
        raw_ledger = [
            (date(2026, 1, 9), "Paycheck", Decimal("3000")),
            (date(2026, 1, 12), "Rent", Decimal("-1500")),
            (date(2026, 1, 23), "Paycheck", Decimal("3000")),
            (date(2026, 1, 25), "Bills", Decimal("-500")),
        ]

        result = process_ledger(raw_ledger, Decimal("1000"), date(2026, 1, 1), date(2026, 1, 31), paycheck_names={"Paycheck"})

        # Two periods: first closed at second paycheck, second is partial (open at window end)
        assert len(result.pay_periods) == 2
        assert result.pay_periods[0].start_date == date(2026, 1, 9)
        assert result.pay_periods[0].end_date == date(2026, 1, 23)
        assert result.pay_periods[0].is_partial is False
        assert result.pay_periods[0].spent == Decimal("1500")

        assert result.pay_periods[1].start_date == date(2026, 1, 23)
        assert result.pay_periods[1].is_partial is True
        assert result.pay_periods[1].spent == Decimal("500")

    def test_tag_based_detection_ignores_name(self):
        """Pay-period detection uses tags, not the entry name."""
        raw_ledger = [
            (date(2026, 1, 9), "Salary Deposit", Decimal("3000")),
            (date(2026, 1, 12), "Rent", Decimal("-1500")),
        ]

        result = process_ledger(
            raw_ledger, Decimal("1000"), date(2026, 1, 1), date(2026, 1, 31),
            paycheck_names={"Salary Deposit"},
        )

        assert len(result.pay_periods) == 1
        assert result.pay_periods[0].start_date == date(2026, 1, 9)

    def test_no_paycheck_means_no_pay_periods(self):
        raw_ledger = [
            (date(2026, 1, 5), "Rent", Decimal("-1500")),
            (date(2026, 1, 10), "Utilities", Decimal("-200")),
        ]

        result = process_ledger(raw_ledger, Decimal("5000"), date(2026, 1, 1), date(2026, 1, 31))

        assert result.pay_periods == []

    def test_inflows_before_same_day_outflows(self):
        """Paycheck entries should sort before same-day outflows."""
        raw_ledger = [
            (date(2026, 1, 15), "Bills", Decimal("-500")),
            (date(2026, 1, 15), "Paycheck", Decimal("3000")),
        ]

        result = process_ledger(raw_ledger, Decimal("1000"), date(2026, 1, 1), date(2026, 1, 31), paycheck_names={"Paycheck"})

        assert result.ledger[0].name == "Paycheck"
        assert result.ledger[1].name == "Bills"


# ---------------------------------------------------------------------------
# Post-processing: balance tracking
# ---------------------------------------------------------------------------


class TestBalanceTracking:
    def test_running_balance_accumulates(self):
        raw_ledger = [
            (date(2026, 1, 1), "Income", Decimal("1000")),
            (date(2026, 1, 5), "Expense", Decimal("-300")),
            (date(2026, 1, 10), "Income", Decimal("500")),
        ]

        result = process_ledger(raw_ledger, Decimal("2000"), date(2026, 1, 1), date(2026, 1, 31))

        assert result.ledger[0].balance == Decimal("3000")
        assert result.ledger[1].balance == Decimal("2700")
        assert result.ledger[2].balance == Decimal("3200")
        assert result.ending_balance == Decimal("3200")

    def test_empty_ledger_returns_initial_balance(self):
        result = process_ledger([], Decimal("5000"), date(2026, 1, 1), date(2026, 1, 31))

        assert result.ending_balance == Decimal("5000")
        assert result.ledger == []
        assert result.months == []
        assert result.pay_periods == []


# ---------------------------------------------------------------------------
# Service layer: build_projection
# ---------------------------------------------------------------------------


class TestBuildProjection:
    @pytest.mark.asyncio
    async def test_returns_correct_shape(self):
        templates = [
            _inflow("Paycheck", 2000.0, MonthDay(day_of_month=15), date(2025, 12, 1)),
            _outflow("Rent", 1200.0, MonthDay(day_of_month=1), date(2025, 12, 1)),
        ]
        initial = Decimal("5000")

        _, raw_ledger = project_cash_on(initial, templates, as_of=date(2026, 3, 31), from_date=date(2026, 1, 1))
        paycheck_names = {t.name for t in templates if TemplateTag.PAYCHECK in t.tags}
        result = process_ledger(raw_ledger, initial, date(2026, 1, 1), date(2026, 3, 31), paycheck_names)

        assert len(result.ledger) == 5  # 3 paychecks + 2 rents (Jan 1 rent excluded by from_date boundary)
        assert len(result.months) == 3

    @pytest.mark.asyncio
    async def test_month_summaries_reflect_net(self):
        templates = [
            _inflow("Income", 3000.0, MonthDay(day_of_month=5), date(2025, 12, 1)),
            _outflow("Expense", 2000.0, MonthDay(day_of_month=20), date(2025, 12, 1)),
        ]
        initial = Decimal("0")

        _, raw_ledger = project_cash_on(initial, templates, as_of=date(2026, 2, 28), from_date=date(2026, 1, 1))
        result = process_ledger(raw_ledger, initial, date(2026, 1, 1), date(2026, 2, 28))

        assert len(result.months) == 2
        assert all(m.net == Decimal("1000") for m in result.months)

    @pytest.mark.asyncio
    async def test_pay_periods_populated_with_paycheck_entries(self):
        templates = [
            CashFlowTemplate(
                name="Paycheck", amount=2000.0, direction=Direction.INFLOW,
                recurrence=WeekdayCadence(interval_weeks=2, weekday=4, anchor_date=date(2026, 1, 23)),
                start_date=date(2026, 1, 23), tags=[TemplateTag.PAYCHECK],
            ),
            _outflow("Rent", 1500.0, MonthDay(day_of_month=1), date(2026, 2, 1)),
        ]
        initial = Decimal("1000")

        _, raw_ledger = project_cash_on(initial, templates, as_of=date(2026, 3, 31), from_date=date(2026, 1, 1))
        paycheck_names = {t.name for t in templates if TemplateTag.PAYCHECK in t.tags}
        result = process_ledger(raw_ledger, initial, date(2026, 1, 1), date(2026, 3, 31), paycheck_names)

        assert len(result.pay_periods) > 0
        assert all(pp.start_date is not None for pp in result.pay_periods)


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------


class TestProjectionEndpoint:
    @pytest.fixture()
    def client(self):
        """Create a TestClient with bypassed auth and no DB (empty projection)."""
        from fastapi.testclient import TestClient

        from app.database import get_db
        from app.dependencies import get_current_user
        from app.main import app

        def _fake_user() -> dict:
            return {"sub": "1", "discord_id": "000", "username": "test-user"}

        async def _no_db():
            yield None

        app.dependency_overrides[get_current_user] = _fake_user
        app.dependency_overrides[get_db] = _no_db
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_new_user_returns_empty_projection(self, client):
        resp = client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

        assert resp.status_code == 200
        body = resp.json()
        assert body["as_of"] == "2026-03-31"
        assert body["from_date"] == "2026-01-01"
        assert body["ledger"] == []
        assert body["months"] == []
        assert body["current_balance"] == "0"
        assert body["has_initial_balance"] is False

    def test_missing_as_of_returns_422(self, client):
        resp = client.get("/api/projection")
        assert resp.status_code == 422
