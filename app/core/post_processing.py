"""Post-processing for raw projection ledgers into structured display data.

Transforms the flat (date, name, delta) ledger from the projection engine
into month summaries and pay-period summaries consumable by both the API
and CLI layers.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.models.schemas import LedgerEntry, MonthSummary, PayPeriodSummary


# ---------------------------------------------------------------------------
# Risk classification — tuning knobs
#
# Adjust these constants to change how aggressively the dashboard flags
# a projection as "tight" or "critical".  All thresholds are based on
# cushion_ratio = lowest_balance / total_outflows.
# ---------------------------------------------------------------------------

#: Below this ratio the projection is classified as "critical".
CUSHION_CRITICAL_THRESHOLD = Decimal("0.10")

#: Below this ratio (but above critical) the projection is "tight".
CUSHION_TIGHT_THRESHOLD = Decimal("0.25")


@dataclass
class ProcessedProjection:
    """Structured output from post-processing a raw projection ledger."""

    ledger: list[LedgerEntry]
    months: list[MonthSummary]
    pay_periods: list[PayPeriodSummary]
    ending_balance: Decimal

    # ── Risk analysis (expenses-before-income walk) ──
    lowest_balance: Decimal = Decimal(0)
    lowest_date: date | None = None
    risk_level: str = "comfortable"
    cushion_ratio: Decimal = Decimal(1)
    total_outflows: Decimal = Decimal(0)
    total_inflows: Decimal = Decimal(0)
    goes_negative: bool = False
    negative_date: date | None = None
    negative_balance: Decimal | None = None

    # ── Derived convenience metrics ──
    days_until_negative: int | None = None  # None = never goes negative.
    drain_rate: Decimal = Decimal(0)        # Avg daily net outflow.
    lowest_ratio: Decimal = Decimal(1)      # lowest_balance / current_balance.


def process_ledger(
    raw_ledger: list[tuple[date, str, Decimal]],
    initial_balance: Decimal,
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

    result = tracker.result()

    # Perform an expenses-before-income walk to find the true intra-day lowest
    # and derive risk classification.  Bills often post before direct deposit,
    # so this ordering exposes dips that end-of-day balances would mask.
    risk = _analyze_risk(raw_ledger, initial_balance, names, window_start, window_end)
    result.lowest_balance = risk.lowest_balance
    result.lowest_date = risk.lowest_date
    result.risk_level = risk.risk_level
    result.cushion_ratio = risk.cushion_ratio
    result.total_outflows = risk.total_outflows
    result.total_inflows = risk.total_inflows
    result.goes_negative = risk.goes_negative
    result.negative_date = risk.negative_date
    result.negative_balance = risk.negative_balance
    result.days_until_negative = risk.days_until_negative
    result.drain_rate = risk.drain_rate
    result.lowest_ratio = risk.lowest_ratio

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_paycheck_entry(entry_name: str, entry_delta: Decimal, paycheck_names: set[str]) -> bool:
    """Check whether this ledger entry belongs to a paycheck template."""
    return entry_delta > 0 and entry_name in paycheck_names


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


@dataclass
class _AccumulationTracker:
    """Walks the sorted ledger once, accumulating month and pay-period summaries."""

    _initial_balance: Decimal
    _window_start: date
    _window_end: date
    _paycheck_names: set[str]

    _running_balance: Decimal = field(init=False)
    _month_net: Decimal = Decimal(0)
    _current_month_key: tuple[int, int] | None = None

    # Pay-period tracking
    _last_paycheck_date: date | None = None
    _period_start_balance: Decimal | None = None
    _period_outflows: Decimal = Decimal(0)
    _period_net: Decimal = Decimal(0)
    _period_min_balance: Decimal | None = None

    # Accumulated results
    _ledger_entries: list[LedgerEntry] = field(default_factory=list)
    _months: list[MonthSummary] = field(default_factory=list)
    _pay_periods: list[PayPeriodSummary] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._running_balance = self._initial_balance

    def process_entry(self, occ_date: date, name: str, delta: Decimal) -> None:
        """Process a single sorted ledger entry."""
        is_paycheck = _is_paycheck_entry(name, delta, self._paycheck_names)

        self._handle_paycheck_boundary(occ_date, is_paycheck)
        self._advance_month(occ_date)

        self._month_net += delta
        self._running_balance += delta

        self._accumulate_period(delta, is_paycheck)

        self._ledger_entries.append(
            LedgerEntry(date=occ_date, name=name, delta=delta, balance=self._running_balance)
        )

    def _handle_paycheck_boundary(self, occ_date: date, is_paycheck: bool) -> None:
        """Close previous pay-period and reset state when a new paycheck arrives."""
        if not is_paycheck:
            return

        if self._last_paycheck_date is not None:
            self._close_period(end_date=occ_date, is_partial=False)

        self._last_paycheck_date = occ_date
        self._period_outflows = Decimal(0)
        self._period_net = Decimal(0)
        self._period_start_balance = None
        self._period_min_balance = None

    def _advance_month(self, occ_date: date) -> None:
        """Detect month boundary and close the previous month summary."""
        key = (occ_date.year, occ_date.month)

        if self._current_month_key is None:
            self._current_month_key = key
        elif key != self._current_month_key:
            self._close_month()
            self._current_month_key = key

    def _accumulate_period(self, delta: Decimal, is_paycheck: bool) -> None:
        """Track running pay-period stats after the balance has been updated."""
        if self._last_paycheck_date is None:
            return

        if is_paycheck:
            self._period_start_balance = self._running_balance
            self._period_min_balance = self._running_balance
            return

        self._period_net += delta

        if delta < 0:
            self._period_outflows += -delta

        if self._period_min_balance is None or self._running_balance < self._period_min_balance:
            self._period_min_balance = self._running_balance

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
        self._month_net = Decimal(0)

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


# ---------------------------------------------------------------------------
# Risk analysis — expenses-before-income walk
# ---------------------------------------------------------------------------


@dataclass
class _RiskAnalysis:
    """Result of the expenses-before-income risk walk."""

    lowest_balance: Decimal
    lowest_date: date | None
    risk_level: str
    cushion_ratio: Decimal
    total_outflows: Decimal
    total_inflows: Decimal
    goes_negative: bool
    negative_date: date | None
    negative_balance: Decimal | None
    days_until_negative: int | None
    drain_rate: Decimal
    lowest_ratio: Decimal


def _analyze_risk(
    raw_ledger: list[tuple[date, str, Decimal]],
    initial_balance: Decimal,
    paycheck_names: set[str],
    window_start: date,
    window_end: date,
) -> _RiskAnalysis:
    """Walk the raw ledger with expenses-before-income ordering per day.

    For each calendar day, outflows are applied first, then inflows.  This
    mirrors how banks typically post debits before credits and exposes
    intra-day balance dips that end-of-day balances would hide.

    Metrics returned (the "tuning knobs"):

    - **cushion_ratio** — ``lowest_balance / total_outflows``.  How much
      buffer remains relative to total obligations.  The primary risk
      input.  Thresholds: see ``CUSHION_CRITICAL_THRESHOLD`` and
      ``CUSHION_TIGHT_THRESHOLD`` at module level.

    - **lowest_ratio** — ``lowest_balance / initial_balance``.  Fraction
      of current balance consumed at the worst point.  Useful as a
      secondary "how scary is this dip" indicator.

    - **drain_rate** — ``(total_outflows - total_inflows) / days``.  Avg
      daily net burn.  Positive = spending exceeds income.

    - **days_until_negative** — calendar days from ``window_start`` to
      the first negative balance.  ``None`` = never.

    - **goes_negative** / **negative_date** / **negative_balance** —
      boolean flag plus the details of the first negative moment.
    """
    if not raw_ledger:
        return _RiskAnalysis(
            lowest_balance=initial_balance,
            lowest_date=None,
            risk_level="comfortable",
            cushion_ratio=Decimal(1),
            total_outflows=Decimal(0),
            total_inflows=Decimal(0),
            goes_negative=False,
            negative_date=None,
            negative_balance=None,
            days_until_negative=None,
            drain_rate=Decimal(0),
            lowest_ratio=Decimal(1),
        )

    # Group entries by date, then split into expenses and income.
    from collections import defaultdict

    by_date: dict[date, list[tuple[str, Decimal]]] = defaultdict(list)
    for occ_date, name, delta in raw_ledger:
        by_date[occ_date].append((name, delta))

    balance = initial_balance
    lowest_balance = balance
    lowest_date: date | None = None
    total_outflows = Decimal(0)
    total_inflows = Decimal(0)
    goes_negative = False
    negative_date: date | None = None
    negative_balance: Decimal | None = None

    for day in sorted(by_date.keys()):
        entries = by_date[day]
        expenses = [(n, d) for n, d in entries if d < 0]
        income = [(n, d) for n, d in entries if d >= 0]

        # Apply expenses first.
        for _, delta in expenses:
            balance += delta
            total_outflows -= delta  # delta is negative, so negate for absolute value.

        # Check for lowest after expenses, before income.
        if balance < lowest_balance:
            lowest_balance = balance
            lowest_date = day

        if balance < 0 and not goes_negative:
            goes_negative = True
            negative_date = day
            negative_balance = balance

        # Then apply income.
        for _, delta in income:
            balance += delta
            total_inflows += delta

        # Also check after income (unlikely to be lower, but thorough).
        if balance < lowest_balance:
            lowest_balance = balance
            lowest_date = day

    # ── Derived metrics ──

    # Days until the first negative balance.
    days_until_negative: int | None = None
    if goes_negative and negative_date is not None:
        days_until_negative = (negative_date - window_start).days

    # Average daily net burn (positive = spending more than earning).
    window_days = max((window_end - window_start).days, 1)
    drain_rate = (total_outflows - total_inflows) / window_days

    # What fraction of the starting balance gets consumed at the worst point.
    if initial_balance > 0:
        lowest_ratio = lowest_balance / initial_balance
    else:
        lowest_ratio = Decimal(0) if lowest_balance <= 0 else Decimal(1)

    # ── Risk classification ──
    #
    # Uses CUSHION_CRITICAL_THRESHOLD and CUSHION_TIGHT_THRESHOLD from
    # module level.  Change those constants to re-tune.
    if goes_negative or lowest_balance < 0:
        risk_level = "critical"
        cushion_ratio = Decimal(0)
    elif total_outflows <= 0:
        risk_level = "comfortable"
        cushion_ratio = Decimal(1)
    else:
        cushion_ratio = lowest_balance / total_outflows
        if cushion_ratio < CUSHION_CRITICAL_THRESHOLD:
            risk_level = "critical"
        elif cushion_ratio < CUSHION_TIGHT_THRESHOLD:
            risk_level = "tight"
        else:
            risk_level = "comfortable"

    return _RiskAnalysis(
        lowest_balance=lowest_balance,
        lowest_date=lowest_date,
        risk_level=risk_level,
        cushion_ratio=cushion_ratio,
        total_outflows=total_outflows,
        total_inflows=total_inflows,
        goes_negative=goes_negative,
        negative_date=negative_date,
        negative_balance=negative_balance,
        days_until_negative=days_until_negative,
        drain_rate=drain_rate,
        lowest_ratio=lowest_ratio,
    )
