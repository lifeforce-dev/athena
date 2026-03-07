"""Teller API client for bank data synchronization.

Uses httpx with mTLS (client certificate) for all Teller API calls.
Certificate and key paths are stored on app.state at startup and injected
by callers (router / background sync task).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import secrets
import time
from typing import Literal

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.models.teller_schemas import (
    TellerAccount,
    TellerBalance,
    TellerTransaction,
)

logger = logging.getLogger(__name__)

_TELLER_BASE_URL = "https://api.teller.io"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class TellerApiError(Exception):
    """Raised when a Teller API call fails after error mapping.

    Attributes:
        status_code: HTTP status (0 for network errors).
        detail: Human-readable description for logging.
    """

    _status_code: int
    _detail: str

    def __init__(self, status_code: int, detail: str) -> None:
        self._status_code = status_code
        self._detail = detail
        super().__init__(detail)

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def detail(self) -> str:
        return self._detail


# ---------------------------------------------------------------------------
# Client builder
# ---------------------------------------------------------------------------


def build_teller_client(
    cert_path: str,
    key_path: str,
    access_token: str,
) -> httpx.AsyncClient:
    """Build an httpx async client configured for Teller mTLS.

    Uses HTTP Basic auth with the access token as the username and an
    empty password, per Teller API requirements.

    The returned client is an async context manager — use ``async with``.
    """
    return httpx.AsyncClient(
        base_url=_TELLER_BASE_URL,
        cert=(cert_path, key_path),
        auth=(access_token, ""),
        timeout=httpx.Timeout(30.0),
    )


# ---------------------------------------------------------------------------
# Centralized API caller
# ---------------------------------------------------------------------------


async def call_teller_api(
    client: httpx.AsyncClient,
    method: Literal["get", "post", "delete"],
    path: str,
    **kwargs: object,
) -> httpx.Response:
    """Centralized Teller API caller with error mapping.

    Routes HTTP status codes to actionable categories:
      - 401/403 → token revoked, mark enrollment disconnected.
      - 429 → rate limited, skip (daily sync retries).
      - Other 4xx/5xx → generic API error.
      - Network failures → wrapped as status_code=0.

    Raises TellerApiError for all failure modes. Callers catch this and
    update enrollment status accordingly.
    """
    try:
        response: httpx.Response = await getattr(client, method)(path, **kwargs)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body = exc.response.text[:200]
        if status in (401, 403):
            raise TellerApiError(
                status,
                "Access token revoked — mark enrollment disconnected",
            ) from exc
        if status == 429:
            raise TellerApiError(status, "Rate limited by Teller API") from exc
        raise TellerApiError(status, f"Teller API {status}: {body}") from exc
    except httpx.RequestError as exc:
        raise TellerApiError(0, f"Network error calling Teller: {exc}") from exc


# ---------------------------------------------------------------------------
# API methods
# ---------------------------------------------------------------------------


async def fetch_accounts(client: httpx.AsyncClient) -> list[TellerAccount]:
    """Fetch all accounts for the authenticated enrollment."""
    response = await call_teller_api(client, "get", "/accounts")
    return [TellerAccount.model_validate(item) for item in response.json()]


async def fetch_balances(
    client: httpx.AsyncClient,
    account_id: str,
) -> TellerBalance:
    """Fetch the balance for a specific account."""
    response = await call_teller_api(
        client, "get", f"/accounts/{account_id}/balances"
    )
    return TellerBalance.model_validate(response.json())


async def fetch_transactions(
    client: httpx.AsyncClient,
    account_id: str,
    count: int = 50,
) -> list[TellerTransaction]:
    """Fetch recent transactions for a specific account.

    Args:
        client: Authenticated httpx client.
        account_id: Teller account identifier.
        count: Maximum number of transactions to return.
    """
    response = await call_teller_api(
        client,
        "get",
        f"/accounts/{account_id}/transactions",
        params={"count": count},
    )
    return [TellerTransaction.model_validate(item) for item in response.json()]


async def delete_enrollment(
    client: httpx.AsyncClient,
    account_id: str,
) -> None:
    """Delete (disconnect) an account via the Teller API.

    Teller may return 404 if the enrollment is already gone; callers
    should handle TellerApiError accordingly.
    """
    await call_teller_api(client, "delete", f"/accounts/{account_id}")


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify a Teller webhook HMAC-SHA256 signature.

    Args:
        payload: Raw request body bytes.
        signature: Value of the X-Teller-Signature header.
        secret: ATHENA_TELLER_WEBHOOK_SECRET from settings.

    Returns:
        True if the computed HMAC matches the provided signature.
    """
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Enrollment nonce generation (stateless via HMAC)
# ---------------------------------------------------------------------------

_NONCE_TTL_SECONDS = 300  # 5 minutes.


def generate_enrollment_nonce(jwt_secret: str) -> tuple[str, str]:
    """Generate a cryptographic nonce for Teller Connect token signing.

    The nonce embeds a timestamp so the server can reject stale values
    without persisting state.  Format: ``{random}:{unix_epoch}``.

    Returns a (nonce, mac) pair. The MAC proves the nonce originated from
    this server and has not been tampered with.
    """
    raw = secrets.token_urlsafe(32)
    nonce = f"{raw}:{int(time.time())}"
    mac = hmac.new(jwt_secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()
    return nonce, mac


def verify_nonce_mac(nonce: str, mac: str, jwt_secret: str) -> bool:
    """Verify that a nonce was generated by this server and is still fresh.

    Recomputes the HMAC and checks the embedded timestamp against a 5-minute
    window.  Returns False for tampered, missing, or expired nonces.
    """
    expected = hmac.new(jwt_secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, mac):
        return False

    # Validate freshness.
    parts = nonce.rsplit(":", 1)
    if len(parts) != 2:
        return False
    try:
        issued_at = int(parts[1])
    except ValueError:
        return False

    return (time.time() - issued_at) <= _NONCE_TTL_SECONDS


# ---------------------------------------------------------------------------
# Ed25519 token signature verification
# ---------------------------------------------------------------------------


def verify_token_signatures(
    *,
    access_token: str,
    nonce: str,
    teller_user_id: str,
    enrollment_id: str,
    environment: str,
    signatures: list[str],
    public_key_b64: str,
) -> bool:
    """Verify that at least one Teller enrollment signature is valid.

    Teller signs ``{nonce}.{accessToken}.{userId}.{enrollmentId}.{environment}``
    using Ed25519. Multiple signatures may be present to support key rotation;
    at least one must verify against the Token Signing Key.

    Args:
        access_token: The enrollment access token from Teller Connect.
        nonce: Server-generated nonce passed to Teller Connect.
        teller_user_id: The ``user.id`` field from the enrollment callback.
        enrollment_id: The ``enrollment.id`` field from the callback.
        environment: Teller environment (sandbox / development / production).
        signatures: Base64-encoded Ed25519 signatures from the callback.
        public_key_b64: Base64-encoded 32-byte Ed25519 public key from dashboard.

    Returns:
        True if at least one signature verifies successfully.
    """
    if not signatures:
        return False

    try:
        key_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(key_bytes)
    except (ValueError, binascii.Error):
        logger.error("Invalid Ed25519 public key — cannot verify enrollment signatures")
        return False

    message = f"{nonce}.{access_token}.{teller_user_id}.{enrollment_id}.{environment}"
    message_bytes = message.encode()

    for sig_b64 in signatures:
        try:
            sig_bytes = base64.b64decode(sig_b64)
            public_key.verify(sig_bytes, message_bytes)
            return True
        except (InvalidSignature, ValueError):
            continue

    logger.warning("No valid Ed25519 signature found for enrollment %s", enrollment_id)
    return False
