"""FastAPI dependencies for authentication and authorization."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.services.auth_service import decode_jwt

logger = logging.getLogger(__name__)

AUTH_COOKIE_NAME = "athena_session"


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    athena_session: Annotated[str | None, Cookie()] = None,
) -> dict:
    """Extract and validate the current user from the session cookie.

    Returns the decoded JWT payload with keys: sub, discord_id, username.
    Raises 401 if the cookie is missing or the token is invalid/expired.
    """
    if not athena_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_jwt(athena_session, settings.jwt_secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return payload
