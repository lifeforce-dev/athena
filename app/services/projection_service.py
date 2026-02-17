from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.post_processing import process_ledger
from app.core.projection import project_cash_on
from app.models.domain import CashFlowConfig, CashFlowTemplate, TemplateTag
from app.models.schemas import ProjectionResponse
from app.repositories import balance_repository, commitment_repository

logger = logging.getLogger(__name__)


class ProjectionConfigError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _load_from_db(
    db: AsyncSession,
    user_id: int,
) -> tuple[Decimal, list[CashFlowTemplate]] | None:
    """Try to load projection inputs from the database.

    Returns (initial_balance, templates) if the user has commitments,
    or None to signal a fallback to the JSON file. This is intentional
    for the current single-user system: new users without DB commitments
    can still see a demo projection from the JSON config.
    """
    templates = await commitment_repository.list_as_templates(db, user_id)
    if not templates:
        return None

    # Use the latest balance snapshot as the starting balance, or 0.
    latest_snapshot = await balance_repository.get_latest(db, user_id)
    initial_balance = latest_snapshot.balance if latest_snapshot else Decimal(0)

    return initial_balance, templates


async def _load_from_json(config_path: Path) -> tuple[Decimal, list[CashFlowTemplate]]:
    """Load projection inputs from the JSON config file."""
    try:
        raw = await asyncio.to_thread(config_path.read_text, encoding='utf-8')
        cfg = CashFlowConfig.from_json(raw)
    except FileNotFoundError as exc:
        logger.exception(f'Projection config file not found. config_path={config_path}')
        raise ProjectionConfigError(status_code=404, detail='Projection config file not found') from exc
    except JSONDecodeError as exc:
        logger.exception(f'Projection config is not valid JSON. config_path={config_path}')
        raise ProjectionConfigError(status_code=422, detail='Projection config is not valid JSON') from exc
    except ValidationError as exc:
        logger.exception(f'Projection config does not match schema. config_path={config_path}')
        raise ProjectionConfigError(status_code=422, detail='Projection config does not match schema') from exc

    return cfg.initial_balance, cfg.templates


async def build_projection(
    config_path: Path,
    as_of: date,
    from_date: date | None,
    db: AsyncSession | None = None,
    user_id: int | None = None,
) -> ProjectionResponse:
    """Build a full projection with month and pay-period summaries.

    If *db* and *user_id* are provided and the user has DB commitments,
    those are used. Otherwise falls back to the JSON config file.
    """
    db_result = None
    if db is not None and user_id is not None:
        db_result = await _load_from_db(db, user_id)

    if db_result is not None:
        initial_balance, templates = db_result
        logger.info(f'Projection using DB data. user_id={user_id} templates={len(templates)}')
    else:
        initial_balance, templates = await _load_from_json(config_path)
        logger.info(f'Projection using JSON fallback. config_path={config_path}')

    if from_date is None:
        from_date = date.today()

    ending, raw_ledger = project_cash_on(
        initial_balance=initial_balance,
        templates=templates,
        as_of=as_of,
        from_date=from_date,
    )

    window_start = min(from_date, as_of)
    window_end = max(from_date, as_of)

    paycheck_names = {t.name for t in templates if TemplateTag.PAYCHECK in t.tags}
    processed = process_ledger(raw_ledger, initial_balance, window_start, window_end, paycheck_names)

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
