"""Data access layer for transactions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Transaction


async def create_from_gmail(
    db: AsyncSession,
    user_id: int,
    amount: Decimal,
    purchase_date: datetime,
    gmail_message_id: str,
    merchant: str | None = None,
    card_last_four: str | None = None,
) -> None:
    """Insert a Gmail-sourced transaction, skipping duplicates.

    Uses INSERT ... ON CONFLICT DO NOTHING against the unique constraint
    on (user_id, gmail_message_id) for idempotency on Pub/Sub retries.
    """
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(Transaction).values(
        user_id=user_id,
        amount=amount,
        purchase_date=purchase_date,
        gmail_message_id=gmail_message_id,
        merchant=merchant,
        card_last_four=card_last_four,
    )
    stmt = stmt.on_conflict_do_nothing(constraint="uq_transaction_user_gmail")
    await db.execute(stmt)


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
