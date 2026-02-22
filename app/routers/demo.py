"""Demo authentication endpoint -- no Discord required.

Hitting POST /api/auth/demo-start will:
  1. Get or create the sandboxed demo user.
  2. Wipe and re-seed their data so every visitor starts fresh.
  3. Issue an athena_session JWT cookie.
  4. Return 200 so the frontend can redirect to the dashboard.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AUTH_COOKIE_NAME
from app.services.auth_service import JWT_TTL_SECONDS, create_jwt
from app.services.demo_service import get_or_create_demo_user, reset_demo_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/demo-start")
async def demo_start(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Create or reset the demo user and issue a session cookie."""
    logger.info("[TourDebug][demo_start] POST /api/auth/demo-start")
    user = await get_or_create_demo_user(db)
    await reset_demo_data(db, user.id)
    await db.commit()
    logger.info("[TourDebug][demo_start] demo user prepared user_id=%s", user.id)

    token = create_jwt(user, settings.jwt_secret)

    response = Response(status_code=204)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=JWT_TTL_SECONDS,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    logger.info("[TourDebug][demo_start] session cookie issued secure=%s", settings.secure_cookies)
    return response
