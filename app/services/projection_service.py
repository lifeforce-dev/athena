from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.post_processing import (
    DEFAULT_CRITICAL_THRESHOLD,
    DEFAULT_TIGHT_THRESHOLD,
    process_ledger,
)
from app.core.projection import project_cash_on
from app.models.domain import CashFlowTemplate, TemplateTag
from app.models.orm import User
from app.models.schemas import ProjectionResponse
from app.repositories import balance_repository, commitment_repository
from app.repositories.commitment_repository import list_active, to_domain

logger = logging.getLogger(__name__)


async def _load_from_db(
    db: AsyncSession,
    user_id: int,
) -> tuple[Decimal, list[CashFlowTemplate], bool] | None:
    """Try to load projection inputs from the database.

    Returns (initial_balance, templates, has_initial_balance) when the
    user has commitments OR a balance snapshot (e.g. from a bank
    connection). Returns None only when the user has neither,
    signaling JSON fallback for brand-new users.
    """
    has_commitments = await commitment_repository.has_any(db, user_id)
    latest_snapshot = await balance_repository.get_latest(db, user_id)

    # User has never set up commitments and has no balance data at all.
    if not has_commitments and latest_snapshot is None:
        return None

    templates = (
        await commitment_repository.list_as_templates(db, user_id)
        if has_commitments
        else []
    )

    initial_balance = latest_snapshot.balance if latest_snapshot else Decimal(0)
    has_initial_balance = latest_snapshot is not None

    return initial_balance, templates, has_initial_balance


async def _load_user_risk_thresholds(
    db: AsyncSession,
    user_id: int,
) -> tuple[Decimal, Decimal]:
    """Look up the user's configured risk thresholds, falling back to defaults."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return DEFAULT_CRITICAL_THRESHOLD, DEFAULT_TIGHT_THRESHOLD
    return user.risk_critical_threshold, user.risk_tight_threshold


async def build_projection(
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
        # User has no commitments yet — return an empty projection.
        initial_balance = Decimal(0)
        templates = []
        has_initial_balance = False
        logger.info(f'Projection empty — user has no commitments. user_id={user_id}')

    if db is not None and user_id is not None:
        critical_threshold, tight_threshold = await _load_user_risk_thresholds(db, user_id)
    else:
        critical_threshold, tight_threshold = DEFAULT_CRITICAL_THRESHOLD, DEFAULT_TIGHT_THRESHOLD

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
    processed = process_ledger(
        raw_ledger,
        initial_balance,
        window_start,
        window_end,
        paycheck_names,
        critical_threshold=critical_threshold,
        tight_threshold=tight_threshold,
    )

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
        lowest_balance=processed.lowest_balance,
        lowest_date=processed.lowest_date,
        risk_level=processed.risk_level,
        total_outflows=processed.total_outflows,
        total_inflows=processed.total_inflows,
        goes_negative=processed.goes_negative,
        negative_date=processed.negative_date,
        negative_balance=processed.negative_balance,
        days_until_negative=processed.days_until_negative,
        drain_rate=processed.drain_rate,
        lowest_ratio=processed.lowest_ratio,
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

    critical_threshold, tight_threshold = await _load_user_risk_thresholds(db, user_id)

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
    processed = process_ledger(
        raw_ledger,
        initial_balance,
        window_start,
        window_end,
        paycheck_names,
        critical_threshold=critical_threshold,
        tight_threshold=tight_threshold,
    )

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
        lowest_balance=processed.lowest_balance,
        lowest_date=processed.lowest_date,
        risk_level=processed.risk_level,
        total_outflows=processed.total_outflows,
        total_inflows=processed.total_inflows,
        goes_negative=processed.goes_negative,
        negative_date=processed.negative_date,
        negative_balance=processed.negative_balance,
        days_until_negative=processed.days_until_negative,
        drain_rate=processed.drain_rate,
        lowest_ratio=processed.lowest_ratio,
    )
