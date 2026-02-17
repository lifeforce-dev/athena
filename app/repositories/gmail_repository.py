"""Data access layer for Gmail push notification state."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import GmailSubscription


async def get_by_email(db: AsyncSession, gmail_address: str) -> GmailSubscription | None:
    """Look up a Gmail subscription by email address."""
    result = await db.execute(
        select(GmailSubscription).where(GmailSubscription.gmail_address == gmail_address)
    )
    return result.scalar_one_or_none()


async def get_by_user(db: AsyncSession, user_id: int) -> GmailSubscription | None:
    """Look up a Gmail subscription by user ID."""
    result = await db.execute(
        select(GmailSubscription).where(GmailSubscription.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_all(db: AsyncSession) -> list[GmailSubscription]:
    """Return all Gmail subscriptions (used by the watch-renewal loop)."""
    result = await db.execute(select(GmailSubscription))
    return list(result.scalars().all())


async def upsert(
    db: AsyncSession,
    user_id: int,
    gmail_address: str,
    history_id: str | None = None,
    watch_expiry: datetime | None = None,
) -> GmailSubscription:
    """Create or update a Gmail subscription for a user."""
    result = await db.execute(
        select(GmailSubscription).where(GmailSubscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.gmail_address = gmail_address
        if history_id is not None:
            sub.history_id = history_id
        if watch_expiry is not None:
            sub.watch_expiry = watch_expiry
    else:
        sub = GmailSubscription(
            user_id=user_id,
            gmail_address=gmail_address,
            history_id=history_id,
            watch_expiry=watch_expiry,
        )
        db.add(sub)

    await db.flush()
    await db.refresh(sub)
    return sub


async def update_history_id(
    db: AsyncSession, subscription_id: int, history_id: str
) -> None:
    """Update the last-processed history ID for a subscription."""
    result = await db.execute(
        select(GmailSubscription).where(GmailSubscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.history_id = history_id
