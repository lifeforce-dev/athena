from __future__ import annotations

import calendar
import math
from collections.abc import Iterable, Iterator
from datetime import date, timedelta
from decimal import Decimal

from app.models.domain import (
    CashFlowTemplate,
    DayInterval,
    MonthDay,
    OneTime,
    WeekdayCadence,
)

# ---------------------------
# Public API
# ---------------------------

def project_cash_on(
    initial_balance: Decimal,
    templates: Iterable[CashFlowTemplate],
    as_of: date,
    from_date: date | None = None,
) -> tuple[Decimal, list[tuple[date, str, Decimal]]]:
    """Run a cash-flow projection and return (ending_balance, ledger)."""
    if from_date is None:
        from_date = date.today()

    start = min(from_date, as_of)
    end = max(from_date, as_of)

    ledger: list[tuple[date, str, Decimal]] = []
    for template in templates:
        for occ in iter_occurrences(template, end):
            # Exclusive start: the initial_balance already reflects from_date.
            if occ <= start:
                continue
            ledger.append((occ, template.name, template.signed_amount))

    ledger.sort(key=lambda t: (t[0], t[1]))

    balance = initial_balance
    for _occ_date, _name, delta in ledger:
        balance += delta

    return balance, ledger


# ---------------------------
# Occurrence engines
# ---------------------------

def iter_occurrences(template: CashFlowTemplate, up_to: date) -> Iterator[date]:
    """Yield every occurrence date for a template up to a limit date."""
    if template.end_date and template.start_date > template.end_date:
        return

    limit = up_to
    if template.end_date and template.end_date < limit:
        limit = template.end_date

    rec = template.recurrence
    if isinstance(rec, WeekdayCadence):
        yield from _iter_weekday_cadence(rec, template.start_date, limit)
    elif isinstance(rec, DayInterval):
        yield from _iter_day_interval(rec, template.start_date, limit)
    elif isinstance(rec, MonthDay):
        yield from _iter_month_day(rec, template.start_date, limit)
    elif isinstance(rec, OneTime):
        if template.start_date <= limit:
            yield template.start_date
    else:
        raise ValueError(f"Unknown recurrence type: {type(rec)}")


def _iter_weekday_cadence(
    spec: WeekdayCadence, start_date: date, limit: date
) -> Iterator[date]:
    anchor = spec.anchor_date
    if anchor.weekday() != spec.weekday:
        anchor = _next_weekday_on_or_after(anchor, spec.weekday)

    if start_date <= anchor:
        first = _next_weekday_on_or_after(start_date, spec.weekday)
        weeks_between = (first - anchor).days // 7
        remainder = weeks_between % spec.interval_weeks
        if remainder != 0:
            first += timedelta(weeks=(spec.interval_weeks - remainder))
    else:
        delta_weeks = (
            math.ceil(((start_date - anchor).days) / 7 / spec.interval_weeks)
            * spec.interval_weeks
        )
        first = anchor + timedelta(weeks=delta_weeks)
        if first.weekday() != spec.weekday:
            first = _next_weekday_on_or_after(first, spec.weekday)

    current = first
    while current <= limit:
        yield current
        current += timedelta(weeks=spec.interval_weeks)


def _iter_day_interval(
    spec: DayInterval, start_date: date, limit: date
) -> Iterator[date]:
    if start_date <= spec.anchor_date:
        current = spec.anchor_date
    else:
        delta_days = (start_date - spec.anchor_date).days
        remainder = delta_days % spec.interval_days
        offset = 0 if remainder == 0 else (spec.interval_days - remainder)
        current = start_date + timedelta(days=offset)

    while current <= limit:
        yield current
        current += timedelta(days=spec.interval_days)


def _iter_month_day(
    spec: MonthDay, start_date: date, limit: date
) -> Iterator[date]:
    year, month = start_date.year, start_date.month
    current = _month_day_or_last(year, month, spec.day_of_month)
    if current < start_date:
        month += 1
        if month == 13:
            month = 1
            year += 1
        current = _month_day_or_last(year, month, spec.day_of_month)

    while current <= limit:
        yield current
        month += 1
        if month == 13:
            month = 1
            year += 1
        current = _month_day_or_last(year, month, spec.day_of_month)


# ---------------------------
# Helpers
# ---------------------------

def _next_weekday_on_or_after(d: date, weekday: int) -> date:
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset)


def _month_day_or_last(y: int, m: int, desired_dom: int) -> date:
    last_dom = calendar.monthrange(y, m)[1]
    dom = min(desired_dom, last_dom)
    return date(y, m, dom)
