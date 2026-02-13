"""Post-processing for raw projection ledgers into structured display data.

Transforms the flat (date, name, delta) ledger from the projection engine
into month summaries and pay-period summaries consumable by both the API
and CLI layers.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date

from app.models.schemas import LedgerEntry, MonthSummary, PayPeriodSummary


@dataclass
class ProcessedProjection:
    """Structured output from post-processing a raw projection ledger."""

    ledger: list[LedgerEntry]
    months: list[MonthSummary]
    pay_periods: list[PayPeriodSummary]
    ending_balance: float


def process_ledger(
    raw_ledger: list[tuple[date, str, float]],
    initial_balance: float,
    window_start: date,
    window_end: date,
    paycheck_names: set[str] | None = None,
) -> ProcessedProjection:
    """Transform a raw projection ledger into structured display data.

    Sorts entries so inflows land before same-day outflows, then accumulates
    month-by-month net totals and pay-period spending summaries.

    Args:
        raw_ledger: Unsorted (date, name, delta) tuples from the projection engine.
        initial_balance: Starting balance before any ledger entries.
        window_start: First date in the projection window.
        window_end: Last date in the projection window.
        paycheck_names: Template names tagged as paychecks. Used for pay-period grouping.

    Returns:
        Structured projection with sorted ledger entries, month summaries,
        and pay-period summaries.
    """
    names = paycheck_names or set()
    sorted_ledger = sorted(
        raw_ledger,
        key=lambda t: (t[0], 0 if _is_paycheck_entry(t[1], t[2], names) else 1, t[1]),
    )

    tracker = _AccumulationTracker(initial_balance, window_start, window_end, names)

    for occ_date, name, delta in sorted_ledger:
        tracker.process_entry(occ_date, name, delta)

    tracker.close()
    return tracker.result()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_paycheck_entry(entry_name: str, entry_delta: float, paycheck_names: set[str]) -> bool:
    """Check whether this ledger entry belongs to a paycheck template."""
    return entry_delta > 0 and entry_name in paycheck_names


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


@dataclass
class _AccumulationTracker:
    """Walks the sorted ledger once, accumulating month and pay-period summaries."""

    _initial_balance: float
    _window_start: date
    _window_end: date
    _paycheck_names: set[str]

    _running_balance: float = field(init=False)
    _month_net: float = 0.0
    _current_month_key: tuple[int, int] | None = None

    # Pay-period tracking
    _last_paycheck_date: date | None = None
    _period_start_balance: float | None = None
    _period_outflows: float = 0.0
    _period_net: float = 0.0
    _period_min_balance: float | None = None

    # Accumulated results
    _ledger_entries: list[LedgerEntry] = field(default_factory=list)
    _months: list[MonthSummary] = field(default_factory=list)
    _pay_periods: list[PayPeriodSummary] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._running_balance = self._initial_balance

    def process_entry(self, occ_date: date, name: str, delta: float) -> None:
        """Process a single sorted ledger entry."""
        is_paycheck = _is_paycheck_entry(name, delta, self._paycheck_names)

        if is_paycheck and self._last_paycheck_date is not None:
            self._close_period(end_date=occ_date, is_partial=False)

        if is_paycheck:
            self._last_paycheck_date = occ_date
            self._period_outflows = 0.0
            self._period_net = 0.0
            self._period_start_balance = None
            self._period_min_balance = None

        key = (occ_date.year, occ_date.month)

        if self._current_month_key is None:
            self._current_month_key = key
        elif key != self._current_month_key:
            self._close_month()
            self._current_month_key = key

        self._month_net += delta
        self._running_balance += delta

        if self._last_paycheck_date is not None:
            if is_paycheck:
                self._period_start_balance = self._running_balance
                self._period_min_balance = self._running_balance
            else:
                self._period_net += delta

                if delta < 0:
                    self._period_outflows += -delta

                if self._period_min_balance is None or self._running_balance < self._period_min_balance:
                    self._period_min_balance = self._running_balance

        self._ledger_entries.append(
            LedgerEntry(date=occ_date, name=name, delta=delta, balance=self._running_balance)
        )

    def close(self) -> None:
        """Flush any open month / pay-period at the end of the ledger."""
        if self._last_paycheck_date is not None:
            self._close_period(end_date=self._window_end, is_partial=True)

        if self._current_month_key is not None:
            self._close_month()

    def result(self) -> ProcessedProjection:
        return ProcessedProjection(
            ledger=self._ledger_entries,
            months=self._months,
            pay_periods=self._pay_periods,
            ending_balance=self._running_balance,
        )

    # -----------------------------------------------------------------------
    # Private
    # -----------------------------------------------------------------------

    def _close_month(self) -> None:
        if self._current_month_key is None:
            return

        year, month = self._current_month_key
        month_start = date(year, month, 1)
        month_end = date(year, month, _last_day_of_month(year, month))
        covered_start = max(self._window_start, month_start)
        covered_end = min(self._window_end, month_end)
        is_partial = covered_start != month_start or covered_end != month_end

        self._months.append(
            MonthSummary(
                month=month,
                year=year,
                net=self._month_net,
                balance=self._running_balance,
                is_partial=is_partial,
                covered_start=covered_start,
                covered_end=covered_end,
            )
        )
        self._month_net = 0.0

    def _close_period(self, end_date: date, is_partial: bool) -> None:
        if (
            self._last_paycheck_date is None
            or self._period_start_balance is None
            or self._period_min_balance is None
        ):
            return

        self._pay_periods.append(
            PayPeriodSummary(
                start_date=self._last_paycheck_date,
                end_date=end_date,
                is_partial=is_partial,
                spent=self._period_outflows,
                net=self._period_net,
                start_balance=self._period_start_balance,
                end_balance=self._running_balance,
                min_balance=self._period_min_balance,
            )
        )
