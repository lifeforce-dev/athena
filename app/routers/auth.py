"""Discord OAuth2 authentication endpoints."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.services.auth_service import (
    JWT_TTL_SECONDS,
    build_discord_auth_url,
    create_jwt,
    create_state_token,
    exchange_code_for_user,
    upsert_user,
    verify_state_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE_NAME = "athena_oauth_state"


@router.get("/login")
async def login(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Redirect to Discord OAuth2 authorization page."""
    state = create_state_token(settings.jwt_secret)
    auth_url = build_discord_auth_url(settings, state)

    response = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # Store state in a short-lived cookie for CSRF verification on callback.
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        max_age=300,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/auth",
    )
    return response


@router.get("/callback")
async def callback(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),
    athena_oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """Handle Discord OAuth2 callback: exchange code, create session."""
    if not athena_oauth_state or athena_oauth_state != state:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid OAuth state",
        )

    if not verify_state_token(state, settings.jwt_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OAuth state expired or tampered",
        )

    try:
        discord_user = await exchange_code_for_user(code, settings)
    except Exception:
        logger.exception("Discord token exchange failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discord authentication failed",
        )

    user = await upsert_user(db, discord_user)
    token = create_jwt(user, settings.jwt_secret)

    logger.info(f"User authenticated: discord_id={user.discord_id} username={user.discord_username}")

    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=JWT_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )

    # Clear the OAuth state cookie.
    response.delete_cookie(key=STATE_COOKIE_NAME, path="/api/auth")
    return response


@router.get("/me")
async def me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Return the current authenticated user's info."""
    return {
        "id": current_user["sub"],
        "discord_id": current_user["discord_id"],
        "username": current_user["username"],
    }


@router.post("/logout")
async def logout() -> Response:
    """Clear the session cookie."""
    response = Response(status_code=status.HTTP_200_OK)
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return response
