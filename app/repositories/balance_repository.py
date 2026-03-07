"""Data access layer for balance snapshots."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import BalanceSnapshot


async def get_latest(db: AsyncSession, user_id: int) -> BalanceSnapshot | None:
    """Return the most recent balance snapshot for a user."""
    result = await db.execute(
        select(BalanceSnapshot)
        .where(BalanceSnapshot.user_id == user_id)
        .order_by(BalanceSnapshot.observed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
) -> list[BalanceSnapshot]:
    """Return recent balance snapshots for a user, newest first."""
    result = await db.execute(
        select(BalanceSnapshot)
        .where(BalanceSnapshot.user_id == user_id)
        .order_by(BalanceSnapshot.observed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_from_teller(
    db: AsyncSession,
    user_id: int,
    balance: Decimal,
    observed_at: datetime,
    account_label: str | None = None,
) -> BalanceSnapshot:
    """Insert a Teller-sourced balance snapshot.

    Unlike Gmail snapshots, Teller balances have no natural dedup key.
    Each sync creates a new row. A previous snapshot at the exact same
    observed_at is unlikely but harmless.
    """
    snapshot = BalanceSnapshot(
        user_id=user_id,
        balance=balance,
        observed_at=observed_at,
        source="teller",
        account_label=account_label,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot


async def create_manual(
    db: AsyncSession,
    user_id: int,
    balance: Decimal,
    observed_at: datetime,
    account_label: str | None = None,
) -> BalanceSnapshot:
    """Insert a manually-reported balance snapshot."""
    snapshot = BalanceSnapshot(
        user_id=user_id,
        balance=balance,
        observed_at=observed_at,
        source="manual",
        account_label=account_label,
    )
    db.add(snapshot)
    await db.flush()
    await db.refresh(snapshot)
    return snapshot
