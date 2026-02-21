"""Dev-only API routes.

These endpoints only exist when ``athena-dev-tools`` is installed.
In production, this package is absent, so there is zero attack surface
-- no routes, no code, no flags to bypass.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.orm import (
    BalanceSnapshot,
    Commitment,
    GmailSubscription,
    Transaction,
    User,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/status")
async def dev_status() -> dict[str, bool]:
    """Return dev mode status. If this endpoint exists, dev mode is on."""
    return {"dev_mode": True}


@router.post("/reset-user", status_code=204)
async def reset_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Wipe all data for the current user and reset profile fields.

    Deletes commitments, balance snapshots, transactions, and gmail
    subscriptions. Resets account_currency, display_currency,
    account_language, completed_tours, and dismissed_modals to NULL.
    """
    for model in (Commitment, BalanceSnapshot, Transaction, GmailSubscription):
        await db.execute(delete(model).where(model.user_id == user_id))

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is not None:
        user.account_currency = None
        user.display_currency = None
        user.account_language = None
        user.completed_tours = None
        user.dismissed_modals = None

    await db.commit()

    logger.info(f"Dev reset completed for user {user_id}")
