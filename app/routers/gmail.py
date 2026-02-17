"""Gmail watch management endpoints.

Provides endpoints to register/renew the Gmail Pub/Sub watch and check its
status. Only authenticated users can manage watches.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.repositories import gmail_repository
from app.services.gmail_service import (
    get_user_email,
    parse_watch_expiry,
    register_watch,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])


class WatchStatusResponse(BaseModel):
    gmail_address: str | None = None
    history_id: str | None = None
    watch_expiry: str | None = None
    is_active: bool = False


class WatchRegisteredResponse(BaseModel):
    gmail_address: str
    history_id: str
    watch_expiry: str


@router.post("/watch", response_model=WatchRegisteredResponse)
async def register_gmail_watch(
    user: Annotated[dict, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: AsyncSession = Depends(get_db),
) -> WatchRegisteredResponse:
    """Register or renew the Gmail Pub/Sub watch for bank notifications.

    Calls the Gmail API users.watch() and stores the resulting historyId
    and expiration in the gmail_subscriptions table.
    """
    user_id = int(user["sub"])

    gmail_address = await get_user_email(settings)
    response = await register_watch(settings)

    history_id = str(response["historyId"])
    watch_expiry = parse_watch_expiry(response["expiration"])

    await gmail_repository.upsert(
        db, user_id, gmail_address, history_id, watch_expiry,
    )

    logger.info(f"Gmail watch registered, expires {watch_expiry.isoformat()}")

    return WatchRegisteredResponse(
        gmail_address=gmail_address,
        history_id=history_id,
        watch_expiry=watch_expiry.isoformat(),
    )


@router.get("/status", response_model=WatchStatusResponse)
async def get_gmail_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> WatchStatusResponse:
    """Check the current Gmail watch status for the authenticated user."""
    user_id = int(user["sub"])
    sub = await gmail_repository.get_by_user(db, user_id)

    if not sub:
        return WatchStatusResponse()

    return WatchStatusResponse(
        gmail_address=sub.gmail_address,
        history_id=sub.history_id,
        watch_expiry=sub.watch_expiry.isoformat() if sub.watch_expiry else None,
        is_active=sub.watch_expiry is not None,
    )
