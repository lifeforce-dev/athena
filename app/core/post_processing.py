"""Post-processing for raw projection ledgers into structured display data.

Transforms the flat (date, name, delta) ledger from the projection engine
into month summaries and pay-period summaries consumable by both the API
and CLI layers.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.models.schemas import LedgerEntry, MonthSummary, PayPeriodSummary

# ---------------------------------------------------------------------------
# Risk classification — defaults for new users
#
# The dashboard verdict is dollar-based: if the projected lowest balance
# falls below these thresholds at any point in the window, the projection
# is flagged "tight" or "critical".  Each user can override these via
# account settings; these values are the defaults used when no override
# is supplied.
# ---------------------------------------------------------------------------

#: Default: lowest balance below this dollar amount → "critical".
DEFAULT_CRITICAL_THRESHOLD = Decimal("500.00")

#: Default: lowest balance below this dollar amount (but above critical) → "tight".
DEFAULT_TIGHT_THRESHOLD = Decimal("1000.00")


@dataclass
class ProcessedProjection:
    """Structured output from post-processing a raw projection ledger."""

    ledger: list[LedgerEntry]
    months: list[MonthSummary]
    pay_periods: list[PayPeriodSummary]
    ending_balance: Decimal

    # ── Risk analysis (end-of-day walk; matches chart trajectory) ──
    lowest_balance: Decimal = Decimal(0)
    lowest_date: date | None = None
    risk_level: str = "comfortable"
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
    critical_threshold: Decimal = DEFAULT_CRITICAL_THRESHOLD,
    tight_threshold: Decimal = DEFAULT_TIGHT_THRESHOLD,
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
        critical_threshold: Lowest balance below this dollar amount classifies the
            projection as "critical".
        tight_threshold: Lowest balance below this dollar amount (but above
            ``critical_threshold``) classifies the projection as "tight".

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

    # Compose risk analysis from single-responsibility pieces.
    # All risk fields (lowest, first-negative, classification) are derived
    # from the same end-of-day walk that drives the chart trajectory line,
    # so the alert never contradicts what the user sees on the chart.
    risk = _analyze_risk(
        raw_ledger,
        initial_balance,
        window_start,
        window_end,
        critical_threshold,
        tight_threshold,
    )
    result.lowest_balance = risk.lowest_balance
    result.lowest_date = risk.lowest_date
    result.risk_level = risk.risk_level
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
# Risk analysis — composable pieces
#
# Each function answers ONE question about the projection.  They are
# composed by ``_analyze_risk`` which the rest of the codebase calls.
#
# All risk fields (lowest balance, first-negative date, classification)
# are derived from the same end-of-day walk that drives the chart line.
# This guarantees the dashboard shortfall banner never contradicts the
# trajectory the user actually sees.
# ---------------------------------------------------------------------------


@dataclass
class _FlowTotals:
    """Absolute sums of money in and money out."""

    total_outflows: Decimal
    total_inflows: Decimal


@dataclass
class _EodWalk:
    """End-of-day walk results — both lowest and first-negative come from
    the same trajectory the chart line plots."""

    lowest_balance: Decimal
    lowest_day: date | None
    goes_negative: bool
    negative_date: date | None
    negative_balance: Decimal | None


@dataclass
class _RiskAnalysis:
    """Composite result — assembled from the pieces above."""

    lowest_balance: Decimal       # End-of-day lowest (matches chart line).
    lowest_date: date | None
    risk_level: str
    total_outflows: Decimal
    total_inflows: Decimal
    goes_negative: bool
    negative_date: date | None
    negative_balance: Decimal | None
    days_until_negative: int | None
    drain_rate: Decimal
    lowest_ratio: Decimal


# ── Piece 1: aggregate flows ───────────────────────────────────────────────

def _sum_flows(
    by_date: dict[date, list[tuple[str, Decimal]]],
) -> _FlowTotals:
    """Sum absolute outflows and inflows across all dates.

    Order-independent — just counts money in and money out.
    """
    total_outflows = Decimal(0)
    total_inflows = Decimal(0)
    for entries in by_date.values():
        for _, delta in entries:
            if delta < 0:
                total_outflows -= delta  # Negate to get positive absolute.
            else:
                total_inflows += delta
    return _FlowTotals(total_outflows=total_outflows, total_inflows=total_inflows)


# ── Piece 2: end-of-day walk (lowest + first-negative) ─────────────────────

def _walk_eod(
    by_date: dict[date, list[tuple[str, Decimal]]],
    initial_balance: Decimal,
) -> _EodWalk:
    """Walk all transactions per day (no special ordering) and capture both
    the minimum end-of-day balance AND the first day it dipped below zero.

    This is exactly what the chart trajectory line plots — after all
    transactions on a given day are settled, what is the balance?  Driving
    every risk field from this single walk guarantees the dashboard alert
    never contradicts the trajectory the user sees.
    """
    balance = initial_balance
    lowest = balance
    lowest_day: date | None = None
    goes_negative = False
    negative_date: date | None = None
    negative_balance: Decimal | None = None

    for day in sorted(by_date.keys()):
        for _, delta in by_date[day]:
            balance += delta

        if balance < lowest:
            lowest = balance
            lowest_day = day

        if balance < 0 and not goes_negative:
            goes_negative = True
            negative_date = day
            negative_balance = balance

    return _EodWalk(
        lowest_balance=lowest,
        lowest_day=lowest_day,
        goes_negative=goes_negative,
        negative_date=negative_date,
        negative_balance=negative_balance,
    )


# ── Piece 3: classify ──────────────────────────────────────────────────────

def _classify_risk(
    eod_lowest: Decimal,
    critical_threshold: Decimal,
    tight_threshold: Decimal,
) -> str:
    """Return the risk label by comparing the end-of-day low to dollar thresholds.

    A negative end-of-day balance is always critical regardless of the
    configured thresholds.  Otherwise the user-configured
    ``critical_threshold`` and ``tight_threshold`` decide.
    """
    if eod_lowest < 0:
        return "critical"
    if eod_lowest < critical_threshold:
        return "critical"
    if eod_lowest < tight_threshold:
        return "tight"
    return "comfortable"


# ── Orchestrator ────────────────────────────────────────────────────────────

def _analyze_risk(
    raw_ledger: list[tuple[date, str, Decimal]],
    initial_balance: Decimal,
    window_start: date,
    window_end: date,
    critical_threshold: Decimal,
    tight_threshold: Decimal,
) -> _RiskAnalysis:
    """Compose the single-responsibility pieces into a full risk analysis.

    Every risk field comes from the same end-of-day trajectory walk, so
    the reported lowest, the negative-balance alert, and the risk-level
    classification are all internally consistent and consistent with the
    chart line.

    - ``lowest_balance`` / ``lowest_date`` — end-of-day minimum.

    - ``goes_negative`` / ``negative_date`` / ``negative_balance`` —
      first day the end-of-day balance drops below zero (if any).

    - ``risk_level`` — comparing the end-of-day low against the supplied
      dollar thresholds.

    - ``total_outflows`` / ``total_inflows`` — absolute flow sums.

    - ``drain_rate`` — average daily net burn.

    - ``lowest_ratio`` — fraction of starting balance consumed at the
      end-of-day worst point.
    """
    if not raw_ledger:
        return _RiskAnalysis(
            lowest_balance=initial_balance,
            lowest_date=None,
            risk_level="comfortable",
            total_outflows=Decimal(0),
            total_inflows=Decimal(0),
            goes_negative=False,
            negative_date=None,
            negative_balance=None,
            days_until_negative=None,
            drain_rate=Decimal(0),
            lowest_ratio=Decimal(1),
        )

    # Group once, reuse across all pieces.
    by_date: dict[date, list[tuple[str, Decimal]]] = defaultdict(list)
    for occ_date, name, delta in raw_ledger:
        by_date[occ_date].append((name, delta))

    flows = _sum_flows(by_date)
    eod = _walk_eod(by_date, initial_balance)
    risk_level = _classify_risk(eod.lowest_balance, critical_threshold, tight_threshold)

    # Derived metrics.
    days_until_negative: int | None = None
    if eod.goes_negative and eod.negative_date is not None:
        days_until_negative = (eod.negative_date - window_start).days

    window_days = max((window_end - window_start).days, 1)
    drain_rate = (flows.total_outflows - flows.total_inflows) / window_days

    if initial_balance > 0:
        lowest_ratio = eod.lowest_balance / initial_balance
    else:
        lowest_ratio = Decimal(0) if eod.lowest_balance <= 0 else Decimal(1)

    return _RiskAnalysis(
        lowest_balance=eod.lowest_balance,
        lowest_date=eod.lowest_day,
        risk_level=risk_level,
        total_outflows=flows.total_outflows,
        total_inflows=flows.total_inflows,
        goes_negative=eod.goes_negative,
        negative_date=eod.negative_date,
        negative_balance=eod.negative_balance,
        days_until_negative=days_until_negative,
        drain_rate=drain_rate,
        lowest_ratio=lowest_ratio,
    )
