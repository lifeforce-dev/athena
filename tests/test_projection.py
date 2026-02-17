"""Tests for the projection engine — occurrence generators and balance math.

These exist to catch regressions when refactoring the core engine.
Each test uses deterministic dates so results never depend on "today".
"""
from __future__ import annotations

import itertools
from datetime import date
from decimal import Decimal

from app.core.projection import iter_occurrences, project_cash_on
from app.models.domain import (
    CashFlowConfig,
    CashFlowTemplate,
    DayInterval,
    Direction,
    MonthDay,
    OneTime,
    WeekdayCadence,
)

# ---------------------------------------------------------------------------
# Helpers — tiny template factories so tests stay readable
# ---------------------------------------------------------------------------

def _inflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.INFLOW, recurrence=recurrence, start_date=start, end_date=end)


def _outflow(name: str, amount: float, recurrence, start: date, end: date | None = None) -> CashFlowTemplate:
    return CashFlowTemplate(name=name, amount=amount, direction=Direction.OUTFLOW, recurrence=recurrence, start_date=start, end_date=end)


# ---------------------------------------------------------------------------
# Occurrence engine: weekday cadence
# ---------------------------------------------------------------------------

class TestWeekdayCadence:
    """Biweekly Friday paychecks are the most important recurrence to get right."""

    def test_biweekly_friday_produces_correct_dates(self):
        # Anchor: Friday 2026-01-23, every 2 weeks
        rec = WeekdayCadence(interval_weeks=2, weekday=4, anchor_date=date(2026, 1, 23))
        t = _inflow("Paycheck", 3877.0, rec, start=date(2026, 1, 23))

        dates = list(iter_occurrences(t, up_to=date(2026, 3, 31)))

        expected = [date(2026, 1, 23), date(2026, 2, 6), date(2026, 2, 20), date(2026, 3, 6), date(2026, 3, 20)]
        assert dates == expected
        assert all(d.weekday() == 4 for d in dates)  # all Fridays

    def test_weekly_sunday(self):
        rec = WeekdayCadence(interval_weeks=1, weekday=6, anchor_date=date(2026, 2, 8))
        t = _outflow("Food", 120.0, rec, start=date(2026, 2, 8))

        dates = list(iter_occurrences(t, up_to=date(2026, 3, 1)))

        assert len(dates) == 4  # Feb 8, 15, 22, Mar 1
        assert all(d.weekday() == 6 for d in dates)

    def test_start_date_after_anchor_aligns_to_cadence(self):
        # Anchor Jan 23, start Feb 1 — should skip to Feb 6 (next cadence hit)
        rec = WeekdayCadence(interval_weeks=2, weekday=4, anchor_date=date(2026, 1, 23))
        t = _inflow("Paycheck", 3877.0, rec, start=date(2026, 2, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 2, 28)))

        assert dates == [date(2026, 2, 6), date(2026, 2, 20)]


# ---------------------------------------------------------------------------
# Occurrence engine: day interval
# ---------------------------------------------------------------------------

class TestDayInterval:
    def test_30_day_interval(self):
        rec = DayInterval(interval_days=30, anchor_date=date(2026, 1, 21))
        t = _outflow("Auto Insurance", 184.48, rec, start=date(2026, 1, 21))

        dates = list(iter_occurrences(t, up_to=date(2026, 4, 30)))

        assert dates[0] == date(2026, 1, 21)
        assert dates[1] == date(2026, 2, 20)
        # Each gap is exactly 30 days
        for a, b in itertools.pairwise(dates):
            assert (b - a).days == 30

    def test_start_date_after_anchor_picks_up_correctly(self):
        rec = DayInterval(interval_days=28, anchor_date=date(2026, 1, 1))
        t = _outflow("Cat Food", 122.0, rec, start=date(2026, 3, 20))

        dates = list(iter_occurrences(t, up_to=date(2026, 5, 31)))

        # First occurrence on or after Mar 20 that aligns with 28-day cadence from Jan 1
        # Jan 1 + 28*N: Jan 29, Feb 26, Mar 26, Apr 23, May 21
        assert dates[0] == date(2026, 3, 26)


# ---------------------------------------------------------------------------
# Occurrence engine: month day
# ---------------------------------------------------------------------------

class TestMonthDay:
    def test_monthly_on_5th(self):
        rec = MonthDay(day_of_month=5)
        t = _outflow("Rent", 2650.0, rec, start=date(2026, 1, 5))

        dates = list(iter_occurrences(t, up_to=date(2026, 4, 30)))

        assert dates == [date(2026, 1, 5), date(2026, 2, 5), date(2026, 3, 5), date(2026, 4, 5)]

    def test_day_31_clamps_to_end_of_short_months(self):
        rec = MonthDay(day_of_month=31)
        t = _outflow("End of month", 100.0, rec, start=date(2026, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 4, 30)))

        assert dates[0] == date(2026, 1, 31)
        assert dates[1] == date(2026, 2, 28)  # Feb clamps to 28
        assert dates[2] == date(2026, 3, 31)
        assert dates[3] == date(2026, 4, 30)  # Apr clamps to 30

    def test_feb_29_in_leap_year(self):
        rec = MonthDay(day_of_month=29)
        t = _outflow("Leap test", 50.0, rec, start=date(2028, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2028, 3, 31)))

        assert dates[1] == date(2028, 2, 29)  # 2028 is a leap year

    def test_feb_29_in_non_leap_year_clamps(self):
        rec = MonthDay(day_of_month=29)
        t = _outflow("Leap test", 50.0, rec, start=date(2026, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 3, 31)))

        assert dates[1] == date(2026, 2, 28)  # 2026 is not a leap year, clamps


# ---------------------------------------------------------------------------
# End date / window boundaries
# ---------------------------------------------------------------------------

class TestEndDate:
    def test_template_with_end_date_stops_generating(self):
        rec = MonthDay(day_of_month=15)
        t = _outflow("Temp sub", 10.0, rec, start=date(2026, 1, 1), end=date(2026, 3, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 12, 31)))

        # Should only get Jan 15 and Feb 15, not Mar 15 (end_date is Mar 1)
        assert dates == [date(2026, 1, 15), date(2026, 2, 15)]

    def test_end_date_before_start_date_yields_nothing(self):
        rec = MonthDay(day_of_month=15)
        t = _outflow("Bad range", 10.0, rec, start=date(2026, 6, 1), end=date(2026, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 12, 31)))

        assert dates == []


# ---------------------------------------------------------------------------
# Balance projection — the main integration point
# ---------------------------------------------------------------------------

class TestProjectCashOn:
    def test_single_inflow_adds_to_balance(self):
        rec = MonthDay(day_of_month=15)
        templates = [_inflow("Paycheck", 1000.0, rec, start=date(2026, 1, 1))]

        balance, ledger = project_cash_on(
            initial_balance=Decimal("500"),
            templates=templates,
            as_of=date(2026, 3, 31),
            from_date=date(2026, 1, 1),
        )

        assert balance == Decimal("3500")  # Jan, Feb, Mar
        assert len(ledger) == 3

    def test_inflow_and_outflow_net_correctly(self):
        pay = _inflow("Paycheck", 2000.0, MonthDay(day_of_month=1), start=date(2026, 1, 1))
        rent = _outflow("Rent", 1500.0, MonthDay(day_of_month=5), start=date(2026, 1, 1))

        balance, _ledger = project_cash_on(
            initial_balance=Decimal("1000"),
            templates=[pay, rent],
            as_of=date(2026, 2, 28),
            from_date=date(2026, 1, 1),
        )

        # 2 paychecks (+4000), 2 rents (-3000), net +1000 from initial 1000
        assert balance == Decimal("2000")

    def test_empty_templates_returns_initial_balance(self):
        balance, ledger = project_cash_on(
            initial_balance=Decimal("5000"),
            templates=[],
            as_of=date(2026, 6, 30),
            from_date=date(2026, 1, 1),
        )

        assert balance == Decimal("5000")
        assert ledger == []

    def test_from_date_filters_out_earlier_occurrences(self):
        rec = MonthDay(day_of_month=15)
        templates = [_inflow("Income", 1000.0, rec, start=date(2026, 1, 1))]

        balance, ledger = project_cash_on(
            initial_balance=Decimal("0"),
            templates=templates,
            as_of=date(2026, 4, 30),
            from_date=date(2026, 3, 1),  # skip Jan + Feb
        )

        assert len(ledger) == 2  # Mar 15, Apr 15 only
        assert balance == Decimal("2000")

    def test_ledger_is_sorted_by_date(self):
        t1 = _outflow("Rent", 2650.0, MonthDay(day_of_month=5), start=date(2026, 1, 1))
        t2 = _inflow("Paycheck", 3877.0, WeekdayCadence(interval_weeks=2, weekday=4, anchor_date=date(2026, 1, 23)), start=date(2026, 1, 23))

        _, ledger = project_cash_on(
            initial_balance=Decimal("8000"),
            templates=[t1, t2],
            as_of=date(2026, 3, 31),
            from_date=date(2026, 1, 1),
        )

        dates_in_ledger = [entry[0] for entry in ledger]
        assert dates_in_ledger == sorted(dates_in_ledger)


# ---------------------------------------------------------------------------
# Config loading from JSON
# ---------------------------------------------------------------------------

class TestConfigParsing:
    def test_round_trip_from_dict(self):
        raw = {
            "initial_balance": 1000.0,
            "templates": [
                {
                    "name": "Test",
                    "amount": 500.0,
                    "direction": "outflow",
                    "recurrence": {"type": "month_day", "day_of_month": 15},
                    "start_date": "2026-01-01",
                }
            ],
        }
        cfg = CashFlowConfig.model_validate(raw)

        assert cfg.initial_balance == Decimal("1000")
        assert len(cfg.templates) == 1
        assert cfg.templates[0].name == "Test"
        assert cfg.templates[0].start_date == date(2026, 1, 1)
        assert isinstance(cfg.templates[0].recurrence, MonthDay)

    def test_round_trip_from_json_string(self):
        import json

        raw = json.dumps({
            "initial_balance": 0.0,
            "templates": [
                {
                    "name": "Pay",
                    "amount": 100.0,
                    "direction": "inflow",
                    "recurrence": {
                        "type": "weekday_cadence",
                        "interval_weeks": 2,
                        "weekday": 4,
                        "anchor_date": "2026-01-23",
                    },
                    "start_date": "2026-01-23",
                }
            ],
        })
        cfg = CashFlowConfig.from_json(raw)

        assert isinstance(cfg.templates[0].recurrence, WeekdayCadence)
        assert cfg.templates[0].recurrence.weekday == 4

    def test_alternative_date_formats(self):
        raw = {
            "initial_balance": 0.0,
            "templates": [
                {
                    "name": "Alt date",
                    "amount": 10.0,
                    "direction": "outflow",
                    "recurrence": {"type": "month_day", "day_of_month": 1},
                    "start_date": "01/15/2026",  # MM/DD/YYYY format
                }
            ],
        }
        cfg = CashFlowConfig.model_validate(raw)

        assert cfg.templates[0].start_date == date(2026, 1, 15)


# ---------------------------------------------------------------------------
# Occurrence engine: one-time
# ---------------------------------------------------------------------------

class TestOneTime:
    def test_one_time_yields_single_date(self):
        rec = OneTime()
        t = _outflow("Security deposit", 500.0, rec, start=date(2026, 3, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 12, 31)))

        assert dates == [date(2026, 3, 1)]

    def test_one_time_excluded_when_before_window(self):
        rec = OneTime()
        t = _outflow("Security deposit", 500.0, rec, start=date(2026, 1, 15))

        balance, ledger = project_cash_on(
            initial_balance=Decimal("1000"),
            templates=[t],
            as_of=date(2026, 6, 30),
            from_date=date(2026, 2, 1),  # window starts after the one-time event
        )

        assert balance == Decimal("1000")
        assert ledger == []

    def test_one_time_included_in_window(self):
        rec = OneTime()
        t = _outflow("Tax payment", 2000.0, rec, start=date(2026, 4, 15))

        balance, ledger = project_cash_on(
            initial_balance=Decimal("5000"),
            templates=[t],
            as_of=date(2026, 6, 30),
            from_date=date(2026, 1, 1),
        )

        assert balance == Decimal("3000")
        assert len(ledger) == 1
        assert ledger[0][1] == "Tax payment"

    def test_one_time_past_projection_window_excluded(self):
        rec = OneTime()
        t = _outflow("Future thing", 100.0, rec, start=date(2027, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 12, 31)))

        assert dates == []

    def test_one_time_with_end_date_respected(self):
        rec = OneTime()
        # end_date before start_date should yield nothing
        t = _outflow("Impossible", 100.0, rec, start=date(2026, 6, 1), end=date(2026, 1, 1))

        dates = list(iter_occurrences(t, up_to=date(2026, 12, 31)))

        assert dates == []

    def test_one_time_from_json(self):
        raw = {
            "initial_balance": 1000.0,
            "templates": [
                {
                    "name": "Bonus",
                    "amount": 3000.0,
                    "direction": "inflow",
                    "recurrence": {"type": "one_time"},
                    "start_date": "2026-03-15",
                }
            ],
        }
        cfg = CashFlowConfig.model_validate(raw)

        assert isinstance(cfg.templates[0].recurrence, OneTime)

        balance, _ = project_cash_on(
            initial_balance=cfg.initial_balance,
            templates=cfg.templates,
            as_of=date(2026, 6, 30),
            from_date=date(2026, 1, 1),
        )

        assert balance == Decimal("4000")
