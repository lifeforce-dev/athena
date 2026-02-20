"""Discord OAuth2 authentication endpoints."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import json

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AUTH_COOKIE_NAME, get_current_user
from app.models.orm import User
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
        secure=settings.secure_cookies,
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
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code is required",
        )

    # verify_state_token uses hmac.compare_digest internally (constant-time).
    if not athena_oauth_state or not verify_state_token(state, settings.jwt_secret, athena_oauth_state):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired OAuth state",
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
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )

    # Clear the OAuth state cookie.
    response.delete_cookie(key=STATE_COOKIE_NAME, path="/api/auth")
    return response


@router.get("/me")
async def me(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return the current authenticated user's info."""
    user_id = int(current_user["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    # Reset display_currency to account_currency on every session init.
    # Display currency is a session-only preference, not persistent.
    if user and user.display_currency != user.account_currency:
        user.display_currency = user.account_currency
        await db.commit()

    return {
        "id": current_user["sub"],
        "discord_id": current_user["discord_id"],
        "username": current_user["username"],
        "account_currency": user.account_currency if user else None,
        "display_currency": user.account_currency if user else None,
        "completed_tours": json.loads(user.completed_tours) if user and user.completed_tours else [],
    }


@router.patch("/me/tour-complete")
async def mark_tour_complete(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    tour_name: str = Query(..., description="Name of the completed tour"),
) -> Response:
    """Mark a specific guided tour as completed for the current user."""
    user_id = int(current_user["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    completed: list[str] = json.loads(user.completed_tours) if user.completed_tours else []

    if tour_name not in completed:
        completed.append(tour_name)
        user.completed_tours = json.dumps(completed)
        await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout")
async def logout() -> Response:
    """Clear the session cookie."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return response
