#!/usr/bin/env python3
"""CLI entrypoint for the cash-flow projection engine."""
from __future__ import annotations

import argparse
import calendar
import logging
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from app.common.logging import setup_logging
from app.core.post_processing import ProcessedProjection, process_ledger
from app.core.projection import project_cash_on
from app.models.domain import CashFlowConfig, TemplateTag, ensure_date, ensure_optional_date
from app.models.schemas import LedgerEntry, MonthSummary, PayPeriodSummary

logger = logging.getLogger(__name__)


def main(out: TextIO = sys.stdout) -> None:
    """Run the projection and write formatted output to the given stream."""
    parser = argparse.ArgumentParser(description="Cash flow projection.")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--as-of", required=True, help="Target date (YYYY-MM-DD)")
    parser.add_argument("--from-date", help="Projection start date (default: today)")
    parser.add_argument("--verbose", action="store_true", help="Show recurrence type in ledger")
    parser.add_argument(
        "--output",
        default="output/projection.txt",
        help="Output file path (default: output/projection.txt)",
    )
    args = parser.parse_args()

    cfg = CashFlowConfig.from_json(Path(args.config).read_text(encoding="utf-8"))

    target = ensure_date(args.as_of)
    start_opt = ensure_optional_date(args.from_date) if args.from_date else None

    ending, raw_ledger = project_cash_on(
        initial_balance=cfg.initial_balance,
        templates=cfg.templates,
        as_of=target,
        from_date=start_opt,
    )

    window_anchor = start_opt if start_opt is not None else date.today()
    window_start = min(window_anchor, target)
    window_end = max(window_anchor, target)

    recurrence_lookup = {t.name: t.recurrence.type for t in cfg.templates}
    paycheck_names = {t.name for t in cfg.templates if TemplateTag.PAYCHECK in t.tags}
    processed = process_ledger(raw_ledger, cfg.initial_balance, window_start, window_end, paycheck_names)

    _write_projection(out, processed, target, ending, recurrence_lookup, args.verbose)
    logger.info(f"Projection complete. balance=${ending:,.2f} entries={len(processed.ledger)}")


def _run_with_output(args_list: list[str] | None = None) -> None:
    """Parse args, run projection, and write output to file."""
    setup_logging()

    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--output", default="output/projection.txt")
    known, _ = pre_parser.parse_known_args(args_list)

    output_path = Path(known.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as fh:
        main(out=fh)

    logger.info(f"Projection written to {output_path}")


# ---------------------------------------------------------------------------
# Private -- text formatting
# ---------------------------------------------------------------------------


def _write_projection(
    out: TextIO,
    processed: ProcessedProjection,
    target: date,
    ending: float,
    recurrence_lookup: dict[str, str],
    verbose: bool,
) -> None:
    """Format the processed projection as human-readable text."""
    out.write(f"As of {target.isoformat()}, projected balance: ${ending:,.2f}\n")
    out.write("\nDetailed ledger:\n")

    month_idx = 0
    period_idx = 0
    current_month_key: tuple[int, int] | None = None

    for entry in processed.ledger:
        entry_month_key = (entry.date.year, entry.date.month)

        # When we cross into a new month, flush the completed month as a footer
        if current_month_key is not None and entry_month_key != current_month_key:
            if month_idx < len(processed.months):
                _write_month_separator(out, processed.months[month_idx])
                month_idx += 1

        current_month_key = entry_month_key

        # Flush any completed pay periods as footers before entries that follow them
        while period_idx < len(processed.pay_periods):
            period = processed.pay_periods[period_idx]

            if not period.is_partial and period.end_date <= entry.date:
                _write_pay_period_summary(out, period)
                period_idx += 1
            else:
                break

        _write_ledger_entry(out, entry, recurrence_lookup, verbose)

    # Flush final month footer
    if month_idx < len(processed.months):
        _write_month_separator(out, processed.months[month_idx])
        month_idx += 1

    # Flush remaining pay periods (partial final period)
    while period_idx < len(processed.pay_periods):
        _write_pay_period_summary(out, processed.pay_periods[period_idx])
        period_idx += 1

    # Flush any remaining months (shouldn't happen, but defensive)
    while month_idx < len(processed.months):
        _write_month_separator(out, processed.months[month_idx])
        month_idx += 1


def _write_ledger_entry(
    out: TextIO,
    entry: LedgerEntry,
    recurrence_lookup: dict[str, str],
    verbose: bool,
) -> None:
    """Write a single ledger entry line."""
    sign = '+' if entry.delta >= 0 else '-'

    if verbose:
        rtype = recurrence_lookup.get(entry.name, 'unknown')
        out.write(f'  [{rtype:17s}] {entry.date.isoformat()}  {entry.name:30s}  {sign}${abs(entry.delta):,.2f}\n')
    else:
        out.write(f'  {entry.date.isoformat()}  {entry.name:30s}  {sign}${abs(entry.delta):,.2f}\n')


def _write_month_separator(out: TextIO, month: MonthSummary) -> None:
    out.write("-" * 42 + "\n")

    if month.is_partial:
        sign = "+" if month.net >= 0 else "-"
        out.write(
            f"{calendar.month_name[month.month]} {month.year} net change "
            f"(partial {month.covered_start.isoformat()} to {month.covered_end.isoformat()}): "
            f"{sign}${abs(month.net):,.2f}  (balance: ${month.balance:,.2f})\n"
        )
    else:
        label = "net gain" if month.net >= 0 else "net loss"
        out.write(
            f"{calendar.month_name[month.month]} {month.year} {label}: ${abs(month.net):,.2f}  "
            f"(balance: ${month.balance:,.2f})\n"
        )


def _write_pay_period_summary(out: TextIO, period: PayPeriodSummary) -> None:
    partial_label = " (partial)" if period.is_partial else ""
    sign = "+" if period.net >= 0 else "-"
    out.write("~" * 42 + "\n")
    out.write(
        f"Between checks ({period.start_date.isoformat()} -> {period.end_date.isoformat()}){partial_label}: "
        f"spent ${period.spent:,.2f}, net {sign}${abs(period.net):,.2f}, "
        f"start ${period.start_balance:,.2f}, end ${period.end_balance:,.2f}, "
        f"min ${period.min_balance:,.2f}\n"
    )
    out.write("\n")


if __name__ == "__main__":
    _run_with_output()
