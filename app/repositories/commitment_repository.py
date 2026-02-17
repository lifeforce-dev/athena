"""Data access layer for commitments with domain model conversion."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models.domain import (
    CashFlowTemplate,
    DayInterval,
    Direction,
    MonthDay,
    OneTime,
    Recurrence,
    TemplateTag,
    WeekdayCadence,
)
from app.models.orm import Commitment

logger = logging.getLogger(__name__)


async def has_any(db: AsyncSession, user_id: int) -> bool:
    """Check if a user has ever created any commitments (active or not).

    Used to distinguish 'never set up' (JSON fallback) from 'cleared all
    commitments' (empty projection).
    """
    result = await db.execute(
        select(func.count()).select_from(Commitment).where(Commitment.user_id == user_id)
    )
    return (result.scalar() or 0) > 0


async def list_active(db: AsyncSession, user_id: int) -> list[Commitment]:
    """Return all active commitments for a user, ordered by name."""
    result = await db.execute(
        select(Commitment)
        .where(Commitment.user_id == user_id, Commitment.is_active.is_(True))
        .order_by(Commitment.name)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, commitment_id: int, user_id: int) -> Commitment | None:
    """Fetch a single commitment scoped to user."""
    result = await db.execute(
        select(Commitment).where(Commitment.id == commitment_id, Commitment.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user_id: int, **fields: object) -> Commitment:
    """Insert a new commitment and return it."""
    commitment = Commitment(user_id=user_id, **fields)
    db.add(commitment)
    await db.flush()
    await db.refresh(commitment)
    return commitment


async def apply_update(
    db: AsyncSession,
    commitment: Commitment,
    **fields: object,
) -> Commitment:
    """Apply field updates to an already-fetched commitment and commit.

    The ORM column's onupdate=func.now() handles updated_at automatically.
    """
    for key, value in fields.items():
        setattr(commitment, key, value)

    await db.flush()
    await db.refresh(commitment)
    return commitment


async def soft_delete(db: AsyncSession, commitment_id: int, user_id: int) -> bool:
    """Soft-delete a commitment by setting is_active=False. Returns True if found.

    Uses a Core-level UPDATE so onupdate= does not fire; updated_at is set explicitly.
    """
    result = await db.execute(
        update(Commitment)
        .where(Commitment.id == commitment_id, Commitment.user_id == user_id)
        .values(is_active=False, updated_at=datetime.now(timezone.utc))
    )

    # CursorResult has rowcount at runtime; type stubs are incomplete.
    return (result.rowcount or 0) > 0  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# ORM -> Domain model conversion
# ---------------------------------------------------------------------------

def _build_recurrence(row: Commitment) -> Recurrence:
    """Convert flat DB columns into the discriminated Recurrence union."""
    freq = row.frequency

    if freq == "daily":
        anchor = row.anchor_date or row.start_date
        return DayInterval(interval_days=1, anchor_date=anchor)

    if freq == "day_interval":
        anchor = row.anchor_date or row.start_date
        return DayInterval(interval_days=row.interval_days or 1, anchor_date=anchor)

    if freq == "weekly":
        anchor = row.anchor_date or row.start_date
        return WeekdayCadence(interval_weeks=1, weekday=anchor.weekday(), anchor_date=anchor)

    if freq == "biweekly":
        anchor = row.anchor_date or row.start_date
        return WeekdayCadence(interval_weeks=2, weekday=anchor.weekday(), anchor_date=anchor)

    if freq == "monthly":
        day = row.day_of_month or row.start_date.day
        return MonthDay(day_of_month=day)

    if freq == "once":
        return OneTime()

    logger.warning("Unsupported frequency '%s' on commitment %d, treating as one-time", freq, row.id)
    return OneTime()


def to_domain(row: Commitment) -> CashFlowTemplate:
    """Convert a Commitment ORM row into a CashFlowTemplate domain object."""
    amount = abs(row.amount)
    direction = Direction.INFLOW if row.amount > 0 else Direction.OUTFLOW
    tags = [TemplateTag.PAYCHECK] if row.is_paycheck else []

    # For one-time items, prefer one_time_date as start_date if set.
    start = row.start_date
    if row.frequency == "once" and row.one_time_date:
        start = row.one_time_date

    return CashFlowTemplate(
        name=row.name,
        amount=amount,
        direction=direction,
        recurrence=_build_recurrence(row),
        start_date=start,
        end_date=row.end_date,
        tags=tags,
    )


async def list_as_templates(db: AsyncSession, user_id: int) -> list[CashFlowTemplate]:
    """Load all active commitments and convert to domain templates."""
    rows = await list_active(db, user_id)
    return [to_domain(row) for row in rows]
