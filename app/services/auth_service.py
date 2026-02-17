"""Discord OAuth2 and JWT token management."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.orm import User

logger = logging.getLogger(__name__)

DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"

JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
STATE_TTL_SECONDS = 5 * 60  # 5 minutes


def build_discord_auth_url(settings: Settings, state: str) -> str:
    """Build the Discord OAuth2 authorization redirect URL."""
    params = httpx.QueryParams(
        client_id=settings.discord_client_id,
        redirect_uri=settings.discord_redirect_uri,
        response_type="code",
        scope="identify",
        state=state,
    )
    return f"{DISCORD_AUTH_URL}?{params}"


async def exchange_code_for_user(
    code: str,
    settings: Settings,
) -> dict:
    """Exchange an OAuth2 authorization code for Discord user info.

    Performs two calls: code -> access token, then token -> user profile.
    """
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        user_resp = await client.get(
            DISCORD_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def upsert_user(db: AsyncSession, discord_user: dict) -> User:
    """Create or update a user from Discord profile data."""
    discord_id = str(discord_user["id"])
    username = discord_user["username"]
    display_name = discord_user.get("global_name")

    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            discord_id=discord_id,
            discord_username=username,
            display_name=display_name,
        )
        db.add(user)
    else:
        user.discord_username = username
        user.display_name = display_name
        user.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)
    return user


def create_jwt(user: User, secret: str) -> str:
    """Create a JWT token for an authenticated user."""
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "discord_id": user.discord_id,
        "username": user.discord_username,
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT token. Returns None on any failure."""
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# OAuth state cookie (CSRF protection)
# ---------------------------------------------------------------------------

def create_state_token(secret: str) -> str:
    """Create a signed, timestamped state token for OAuth CSRF protection."""
    payload = {"ts": int(time.time())}
    data = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
    return f"{data.decode()}.{sig}"


def verify_state_token(token: str, secret: str, expected_token: str | None = None) -> bool:
    """Verify a state token's signature, cookie match, and expiry.

    When *expected_token* is provided (the cookie value), comparison is
    constant-time via hmac.compare_digest to avoid timing side-channels.
    """
    if expected_token is not None and not hmac.compare_digest(token, expected_token):
        return False

    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return False

    data_str, sig = parts

    expected_sig = hmac.new(secret.encode(), data_str.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False

    try:
        payload = json.loads(data_str)
    except json.JSONDecodeError:
        return False

    elapsed = int(time.time()) - payload.get("ts", 0)
    return 0 <= elapsed <= STATE_TTL_SECONDS
