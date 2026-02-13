from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from app.core.post_processing import process_ledger
from app.core.projection import project_cash_on
from app.models.domain import CashFlowConfig, TemplateTag
from app.models.schemas import ProjectionResponse

logger = logging.getLogger(__name__)


def build_projection(config_path: Path, as_of: date, from_date: date | None) -> ProjectionResponse:
    """Build a full projection with month and pay-period summaries."""
    cfg = CashFlowConfig.from_json(config_path.read_text(encoding='utf-8'))

    if from_date is None:
        from_date = date.today()

    ending, raw_ledger = project_cash_on(
        initial_balance=cfg.initial_balance,
        templates=cfg.templates,
        as_of=as_of,
        from_date=from_date,
    )

    window_start = min(from_date, as_of)
    window_end = max(from_date, as_of)

    paycheck_names = {t.name for t in cfg.templates if TemplateTag.PAYCHECK in t.tags}
    processed = process_ledger(raw_ledger, cfg.initial_balance, window_start, window_end, paycheck_names)

    logger.info(
        f'Projection built. entries={len(processed.ledger)} '
        f'months={len(processed.months)} pay_periods={len(processed.pay_periods)}'
    )

    return ProjectionResponse(
        as_of=as_of,
        from_date=from_date,
        current_balance=ending,
        ledger=processed.ledger,
        months=processed.months,
        pay_periods=processed.pay_periods,
    )
