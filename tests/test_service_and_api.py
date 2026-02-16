"""Tests for post-processing, the projection service, and the API endpoint.

Covers the shared accumulation logic (month summaries, pay-period grouping)
and the full request/response cycle through FastAPI.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.core.post_processing import process_ledger
from app.models.domain import (
    CashFlowConfig,
    CashFlowTemplate,
    DayInterval,
    Direction,
    MonthDay,
    OneTime,
    TemplateTag,
    WeekdayCadence,
)
from app.models.schemas import MonthSummary, PayPeriodSummary
from app.services.projection_service import build_projection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.INFLOW, recurrence=recurrence, start_date=start, end_date=end)


def _outflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.OUTFLOW, recurrence=recurrence, start_date=start, end_date=end)


def _write_config(tmp_path: Path, cfg: dict) -> Path:
    config_path = tmp_path / "test_config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    return config_path


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
            (date(2026, 1, 5), "Rent", -1500.0),
            (date(2026, 1, 15), "Paycheck", 3000.0),
        ]

        result = process_ledger(raw_ledger, 5000.0, date(2026, 1, 1), date(2026, 1, 31))

        assert len(result.months) == 1
        assert result.months[0].month == 1
        assert result.months[0].year == 2026
        assert result.months[0].net == pytest.approx(1500.0)
        assert result.months[0].is_partial is False

    def test_multiple_months_each_get_summary(self):
        raw_ledger = [
            (date(2026, 1, 15), "Income", 2000.0),
            (date(2026, 2, 15), "Income", 2000.0),
            (date(2026, 3, 15), "Income", 2000.0),
        ]

        result = process_ledger(raw_ledger, 0.0, date(2026, 1, 1), date(2026, 3, 31))

        assert len(result.months) == 3
        assert [m.month for m in result.months] == [1, 2, 3]
        assert all(m.net == pytest.approx(2000.0) for m in result.months)

    def test_partial_month_flagged(self):
        raw_ledger = [(date(2026, 2, 15), "Income", 1000.0)]

        result = process_ledger(raw_ledger, 0.0, date(2026, 2, 10), date(2026, 2, 28))

        assert result.months[0].is_partial is True
        assert result.months[0].covered_start == date(2026, 2, 10)


# ---------------------------------------------------------------------------
# Post-processing: pay-period grouping
# ---------------------------------------------------------------------------


class TestPayPeriodGrouping:
    def test_paycheck_entries_create_pay_periods(self):
        raw_ledger = [
            (date(2026, 1, 9), "Paycheck", 3000.0),
            (date(2026, 1, 12), "Rent", -1500.0),
            (date(2026, 1, 23), "Paycheck", 3000.0),
            (date(2026, 1, 25), "Bills", -500.0),
        ]

        result = process_ledger(raw_ledger, 1000.0, date(2026, 1, 1), date(2026, 1, 31), paycheck_names={"Paycheck"})

        # Two periods: first closed at second paycheck, second is partial (open at window end)
        assert len(result.pay_periods) == 2
        assert result.pay_periods[0].start_date == date(2026, 1, 9)
        assert result.pay_periods[0].end_date == date(2026, 1, 23)
        assert result.pay_periods[0].is_partial is False
        assert result.pay_periods[0].spent == pytest.approx(1500.0)

        assert result.pay_periods[1].start_date == date(2026, 1, 23)
        assert result.pay_periods[1].is_partial is True
        assert result.pay_periods[1].spent == pytest.approx(500.0)

    def test_tag_based_detection_ignores_name(self):
        """Pay-period detection uses tags, not the entry name."""
        raw_ledger = [
            (date(2026, 1, 9), "Salary Deposit", 3000.0),
            (date(2026, 1, 12), "Rent", -1500.0),
        ]

        result = process_ledger(
            raw_ledger, 1000.0, date(2026, 1, 1), date(2026, 1, 31),
            paycheck_names={"Salary Deposit"},
        )

        assert len(result.pay_periods) == 1
        assert result.pay_periods[0].start_date == date(2026, 1, 9)

    def test_no_paycheck_means_no_pay_periods(self):
        raw_ledger = [
            (date(2026, 1, 5), "Rent", -1500.0),
            (date(2026, 1, 10), "Utilities", -200.0),
        ]

        result = process_ledger(raw_ledger, 5000.0, date(2026, 1, 1), date(2026, 1, 31))

        assert result.pay_periods == []

    def test_inflows_before_same_day_outflows(self):
        """Paycheck entries should sort before same-day outflows."""
        raw_ledger = [
            (date(2026, 1, 15), "Bills", -500.0),
            (date(2026, 1, 15), "Paycheck", 3000.0),
        ]

        result = process_ledger(raw_ledger, 1000.0, date(2026, 1, 1), date(2026, 1, 31), paycheck_names={"Paycheck"})

        assert result.ledger[0].name == "Paycheck"
        assert result.ledger[1].name == "Bills"


# ---------------------------------------------------------------------------
# Post-processing: balance tracking
# ---------------------------------------------------------------------------


class TestBalanceTracking:
    def test_running_balance_accumulates(self):
        raw_ledger = [
            (date(2026, 1, 1), "Income", 1000.0),
            (date(2026, 1, 5), "Expense", -300.0),
            (date(2026, 1, 10), "Income", 500.0),
        ]

        result = process_ledger(raw_ledger, 2000.0, date(2026, 1, 1), date(2026, 1, 31))

        assert result.ledger[0].balance == pytest.approx(3000.0)
        assert result.ledger[1].balance == pytest.approx(2700.0)
        assert result.ledger[2].balance == pytest.approx(3200.0)
        assert result.ending_balance == pytest.approx(3200.0)

    def test_empty_ledger_returns_initial_balance(self):
        result = process_ledger([], 5000.0, date(2026, 1, 1), date(2026, 1, 31))

        assert result.ending_balance == pytest.approx(5000.0)
        assert result.ledger == []
        assert result.months == []
        assert result.pay_periods == []


# ---------------------------------------------------------------------------
# Service layer: build_projection
# ---------------------------------------------------------------------------


class TestBuildProjection:
    def test_returns_correct_shape(self, tmp_path: Path):
        config = {
            "initial_balance": 5000.0,
            "templates": [
                {
                    "name": "Paycheck",
                    "amount": 2000.0,
                    "direction": "inflow",
                    "recurrence": {"type": "month_day", "day_of_month": 15},
                    "start_date": "2026-01-01",
                    "tags": ["paycheck"],
                },
                {
                    "name": "Rent",
                    "amount": 1200.0,
                    "direction": "outflow",
                    "recurrence": {"type": "month_day", "day_of_month": 1},
                    "start_date": "2026-01-01",
                },
            ],
        }
        config_path = _write_config(tmp_path, config)

        result = build_projection(config_path, as_of=date(2026, 3, 31), from_date=date(2026, 1, 1))

        assert result.as_of == date(2026, 3, 31)
        assert result.from_date == date(2026, 1, 1)
        assert len(result.ledger) == 6  # 3 paychecks + 3 rents
        assert len(result.months) == 3
        assert result.current_balance == pytest.approx(5000.0 + 3 * 2000.0 - 3 * 1200.0)

    def test_month_summaries_reflect_net(self, tmp_path: Path):
        config = {
            "initial_balance": 0.0,
            "templates": [
                {
                    "name": "Income",
                    "amount": 3000.0,
                    "direction": "inflow",
                    "recurrence": {"type": "month_day", "day_of_month": 1},
                    "start_date": "2026-01-01",
                },
                {
                    "name": "Expense",
                    "amount": 2000.0,
                    "direction": "outflow",
                    "recurrence": {"type": "month_day", "day_of_month": 15},
                    "start_date": "2026-01-01",
                },
            ],
        }
        config_path = _write_config(tmp_path, config)

        result = build_projection(config_path, as_of=date(2026, 2, 28), from_date=date(2026, 1, 1))

        assert len(result.months) == 2
        assert all(m.net == pytest.approx(1000.0) for m in result.months)

    def test_pay_periods_populated_with_paycheck_entries(self, tmp_path: Path):
        config = {
            "initial_balance": 1000.0,
            "templates": [
                {
                    "name": "Paycheck",
                    "amount": 2000.0,
                    "direction": "inflow",
                    "recurrence": {
                        "type": "weekday_cadence",
                        "interval_weeks": 2,
                        "weekday": 4,
                        "anchor_date": "2026-01-23",
                    },
                    "start_date": "2026-01-23",
                    "tags": ["paycheck"],
                },
                {
                    "name": "Rent",
                    "amount": 1500.0,
                    "direction": "outflow",
                    "recurrence": {"type": "month_day", "day_of_month": 1},
                    "start_date": "2026-02-01",
                },
            ],
        }
        config_path = _write_config(tmp_path, config)

        result = build_projection(config_path, as_of=date(2026, 3, 31), from_date=date(2026, 1, 1))

        assert len(result.pay_periods) > 0
        assert all(pp.start_date is not None for pp in result.pay_periods)


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------


class TestProjectionEndpoint:
    @pytest.fixture()
    def client(self, tmp_path: Path):
        """Create a TestClient with a temp config file."""
        from fastapi.testclient import TestClient

        config = {
            "initial_balance": 1000.0,
            "templates": [
                {
                    "name": "Income",
                    "amount": 500.0,
                    "direction": "inflow",
                    "recurrence": {"type": "month_day", "day_of_month": 15},
                    "start_date": "2026-01-01",
                },
            ],
        }
        config_path = _write_config(tmp_path, config)

        # Override settings to use test config
        from app.config import Settings, get_settings
        from app.main import app

        def _override_settings() -> Settings:
            return Settings(config_path=config_path)

        app.dependency_overrides[get_settings] = _override_settings
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_get_projection_returns_200(self, client):
        resp = client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

        assert resp.status_code == 200
        body = resp.json()
        assert body["as_of"] == "2026-03-31"
        assert body["from_date"] == "2026-01-01"
        assert len(body["ledger"]) == 3  # Jan, Feb, Mar on the 15th
        assert body["current_balance"] == pytest.approx(2500.0)

    def test_get_projection_returns_months(self, client):
        resp = client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

        body = resp.json()
        assert len(body["months"]) == 3
        assert all(m["net"] == pytest.approx(500.0) for m in body["months"])

    def test_missing_as_of_returns_422(self, client):
        resp = client.get("/api/projection")
        assert resp.status_code == 422

    def test_missing_config_file_returns_404(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from app.config import Settings, get_settings
        from app.main import app

        missing_config_path = tmp_path / "missing_config.json"

        def _override_settings() -> Settings:
            return Settings(config_path=missing_config_path)

        app.dependency_overrides[get_settings] = _override_settings
        try:
            with TestClient(app) as test_client:
                resp = test_client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

            assert resp.status_code == 404
            assert resp.json() == {"detail": "Projection config file not found"}
        finally:
            app.dependency_overrides.clear()

    def test_invalid_json_config_returns_422(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from app.config import Settings, get_settings
        from app.main import app

        invalid_json_path = tmp_path / "invalid_json_config.json"
        invalid_json_path.write_text('{"initial_balance": 1000, "templates": [}', encoding="utf-8")

        def _override_settings() -> Settings:
            return Settings(config_path=invalid_json_path)

        app.dependency_overrides[get_settings] = _override_settings
        try:
            with TestClient(app) as test_client:
                resp = test_client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

            assert resp.status_code == 422
            assert resp.json() == {"detail": "Projection config is not valid JSON"}
        finally:
            app.dependency_overrides.clear()

    def test_schema_invalid_config_returns_422(self, tmp_path: Path):
        from fastapi.testclient import TestClient

        from app.config import Settings, get_settings
        from app.main import app

        invalid_schema_path = tmp_path / "invalid_schema_config.json"
        invalid_schema_path.write_text(
            json.dumps(
                {
                    "initial_balance": 1000.0,
                    "templates": [
                        {
                            "name": "Income",
                            "direction": "inflow",
                            "recurrence": {"type": "month_day", "day_of_month": 15},
                            "start_date": "2026-01-01",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        def _override_settings() -> Settings:
            return Settings(config_path=invalid_schema_path)

        app.dependency_overrides[get_settings] = _override_settings
        try:
            with TestClient(app) as test_client:
                resp = test_client.get("/api/projection?as_of=2026-03-31&from_date=2026-01-01")

            assert resp.status_code == 422
            assert resp.json() == {"detail": "Projection config does not match schema"}
        finally:
            app.dependency_overrides.clear()
