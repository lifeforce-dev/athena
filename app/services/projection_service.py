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
from app.repositories.commitment_repository import list_active, to_domain

logger = logging.getLogger(__name__)


class ProjectionConfigError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def _load_from_db(
    db: AsyncSession,
    user_id: int,
) -> tuple[Decimal, list[CashFlowTemplate], bool] | None:
    """Try to load projection inputs from the database.

    Returns (initial_balance, templates) if the user has ever created
    commitments (even if all are now inactive). Returns None only when
    the user has zero commitment rows, signaling JSON fallback for
    users who have not yet set up their data.
    """
    # Distinguish 'never set up' from 'cleared all commitments'.
    if not await commitment_repository.has_any(db, user_id):
        return None

    templates = await commitment_repository.list_as_templates(db, user_id)

    # Use the latest balance snapshot as the starting balance, or 0.
    latest_snapshot = await balance_repository.get_latest(db, user_id)
    initial_balance = latest_snapshot.balance if latest_snapshot else Decimal(0)
    has_initial_balance = latest_snapshot is not None

    return initial_balance, templates, has_initial_balance


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
        initial_balance, templates, has_initial_balance = db_result
        logger.info(f'Projection using DB data. user_id={user_id} templates={len(templates)}')
    else:
        initial_balance, templates = await _load_from_json(config_path)
        # JSON config always provides an explicit initial_balance.
        has_initial_balance = True
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
        current_balance=initial_balance,
        has_initial_balance=has_initial_balance,
        ledger=processed.ledger,
        months=processed.months,
        pay_periods=processed.pay_periods,
    )


async def build_scenario_projection(
    as_of: date,
    from_date: date | None,
    excluded_ids: list[int],
    amount_overrides: dict[int, Decimal],
    db: AsyncSession,
    user_id: int,
) -> ProjectionResponse:
    """Build a projection with commitment overrides for what-if scenarios.

    Loads all active commitments, applies exclusions and amount changes,
    then runs the normal projection pipeline.
    """
    rows = await list_active(db, user_id)

    # Filter out excluded commitments and apply amount overrides.
    templates: list[CashFlowTemplate] = []
    for row in rows:
        if row.id in excluded_ids:
            continue
        if row.id in amount_overrides:
            row.amount = amount_overrides[row.id]
        templates.append(to_domain(row))

    latest_snapshot = await balance_repository.get_latest(db, user_id)
    initial_balance = latest_snapshot.balance if latest_snapshot else Decimal(0)
    has_initial_balance = latest_snapshot is not None

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
        f'Scenario projection built. user_id={user_id} excluded={len(excluded_ids)} '
        f'overrides={len(amount_overrides)} entries={len(processed.ledger)}'
    )

    return ProjectionResponse(
        as_of=as_of,
        from_date=from_date,
        current_balance=initial_balance,
        has_initial_balance=has_initial_balance,
        ledger=processed.ledger,
        months=processed.months,
        pay_periods=processed.pay_periods,
    )
