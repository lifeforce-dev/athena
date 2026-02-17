"""Pub/Sub push notification receiver for Gmail bank notifications.

Google Pub/Sub delivers a push when new email arrives. This endpoint:
1. Verifies the OIDC bearer token from Google.
2. Fetches new messages via Gmail history.list.
3. Parses BofA bank emails (balance + debit card).
4. Stores parsed data with ON CONFLICT DO NOTHING for idempotency.
5. Returns 200 quickly to acknowledge receipt.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.repositories import balance_repository, gmail_repository, transaction_repository
from app.services.email_parser import (
    BOA_SENDER,
    BalanceNotification,
    try_parse_email,
)
from app.services.gmail_service import (
    extract_body_html,
    extract_header,
    fetch_history_message_ids,
    get_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notifications"])


# -- Pub/Sub payload models ------------------------------------------------


class PubSubMessage(BaseModel):
    """Inner message from a Pub/Sub push delivery."""

    data: str
    messageId: str | None = None
    publishTime: str | None = None


class PubSubPush(BaseModel):
    """Top-level payload from a Pub/Sub push subscription."""

    message: PubSubMessage
    subscription: str | None = None


# -- OIDC verification -----------------------------------------------------


async def _verify_oidc_token(request: Request, settings: Settings) -> bool:
    """Verify the OIDC bearer token from Google Pub/Sub.

    Returns True if the token is valid. Skips verification if no audience
    is configured (allows local dev without GCP).
    """
    if not settings.google_push_audience:
        logger.warning("OIDC verification skipped -- no google_push_audience configured")
        return True

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[7:]

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        claims = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            token,
            google_requests.Request(),
            settings.google_push_audience,
        )
        logger.info(f"OIDC token verified, email={claims.get('email')}")
        return True
    except Exception:
        logger.exception("OIDC token verification failed")
        return False


# -- Message processing ----------------------------------------------------


async def _process_message(
    db: AsyncSession,
    user_id: int,
    settings: Settings,
    gmail_message_id: str,
) -> bool:
    """Fetch, parse, and store a single Gmail message.

    Returns True if a balance or transaction record was stored.
    """
    message = await get_message(settings, gmail_message_id)

    sender = extract_header(message, "From") or ""
    if BOA_SENDER not in sender.lower():
        return False

    subject = extract_header(message, "Subject") or ""
    html = extract_body_html(message)
    if not html:
        logger.warning(f"No HTML body in message {gmail_message_id}")
        return False

    notification = try_parse_email(subject, html)
    if notification is None:
        logger.info(f"Unrecognized BofA email subject: {subject[:80]}")
        return False

    if isinstance(notification, BalanceNotification):
        await balance_repository.create_from_gmail(
            db,
            user_id,
            notification.balance,
            notification.observed_at,
            gmail_message_id,
            notification.account_label,
        )
        logger.info("Balance snapshot recorded from Gmail")
    else:
        await transaction_repository.create_from_gmail(
            db,
            user_id,
            notification.amount,
            notification.purchase_date,
            gmail_message_id,
            notification.merchant,
            notification.card_last_four,
        )
        logger.info("Transaction recorded from Gmail")

    return True


# -- Push endpoint ---------------------------------------------------------


@router.post("/notifications/gmail/push")
async def handle_gmail_push(
    request: Request,
    push: PubSubPush,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Receive a Gmail Pub/Sub push notification.

    Verifies the OIDC token, fetches new messages via the Gmail API,
    parses BofA bank emails, and stores balance/transaction data.
    Always returns 200 to acknowledge receipt (Pub/Sub retries on non-2xx).
    """
    if not await _verify_oidc_token(request, settings):
        return Response(status_code=403)

    # Decode the Pub/Sub message data.
    try:
        decoded = json.loads(base64.urlsafe_b64decode(push.message.data))
        email_address = decoded.get("emailAddress", "")
        push_history_id = str(decoded.get("historyId", ""))
    except Exception:
        logger.exception("Failed to decode Pub/Sub message data")
        return Response(status_code=200)

    # Resolve the user by their registered Gmail address.
    sub = await gmail_repository.get_by_email(db, email_address)
    if not sub:
        logger.warning("No Gmail subscription found for push notification")
        return Response(status_code=200)

    start_id = sub.history_id or push_history_id

    try:
        message_ids = await fetch_history_message_ids(settings, start_id)
        logger.info(f"Processing {len(message_ids)} new Gmail message(s)")

        for msg_id in message_ids:
            try:
                await _process_message(db, sub.user_id, settings, msg_id)
            except Exception:
                logger.exception(f"Failed to process message {msg_id}")

        await db.commit()
    except Exception:
        logger.exception("Gmail history fetch/processing failed")

    # Always advance history ID to prevent reprocessing loops.
    # If processing failed, the next push catches up via historyId.
    try:
        await gmail_repository.update_history_id(db, sub.id, push_history_id)
    except Exception:
        logger.exception("Failed to update Gmail history ID")

    return Response(status_code=200)
