"""Data access layer for transactions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Transaction


async def create_from_teller(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    purchase_date: datetime,
    teller_transaction_id: str,
    merchant: str | None = None,
    category: str | None = None,
) -> bool:
    """Insert a Teller-sourced transaction, skipping duplicates.

    Uses INSERT ... ON CONFLICT DO NOTHING against the unique constraint
    on (user_id, teller_transaction_id) for idempotency on webhook retries.
    Returns True if a row was actually inserted, False if skipped.
    """
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(Transaction).values(
        user_id=user_id,
        amount=amount,
        purchase_date=purchase_date,
        source="teller",
        teller_transaction_id=teller_transaction_id,
        merchant=merchant,
        category=category,
    )
    stmt = stmt.on_conflict_do_nothing(constraint="uq_transaction_user_teller")
    result = await db.execute(stmt)
    return result.rowcount > 0  # type: ignore[union-attr]


async def list_recent(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
) -> list[Transaction]:
    """Return recent transactions for a user, newest first."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.purchase_date.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
