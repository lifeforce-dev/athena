"""Teller bank integration endpoints.

Handles enrollment (Teller Connect callback), status polling,
disconnection, and webhook ingestion.
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError as DBIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.encryption import decrypt_token, encrypt_token
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.teller_constants import TellerStatus
from app.models.teller_schemas import (
    TellerAccountOption,
    TellerEnrollRequest,
    TellerEnrollResponse,
    TellerNonceResponse,
    TellerSelectAccountRequest,
    TellerStatusResponse,
)
from app.repositories import balance_repository, teller_repository, transaction_repository
from app.services.currency_service import convert_amount, get_user_account_currency
from app.services.teller_service import (
    TellerApiError,
    build_teller_client,
    delete_enrollment,
    fetch_accounts,
    fetch_balances,
    fetch_transactions,
    generate_enrollment_nonce,
    verify_nonce_mac,
    verify_token_signatures,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teller", tags=["teller"])


# ---------------------------------------------------------------------------
# GET /teller/nonce
# ---------------------------------------------------------------------------


@router.get("/nonce")
async def get_nonce(
    user_id: Annotated[int, Depends(get_current_user_id)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TellerNonceResponse:
    """Generate a cryptographic nonce for Teller Connect token signing.

    The frontend fetches this before opening TellerConnect and passes the
    nonce to the SDK.  On enrollment, the nonce + HMAC are sent back for
    stateless verification.
    """
    nonce, mac = generate_enrollment_nonce(settings.jwt_secret)
    return TellerNonceResponse(nonce=nonce, nonce_mac=mac)


# ---------------------------------------------------------------------------
# POST /teller/enroll
# ---------------------------------------------------------------------------


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll(
    body: TellerEnrollRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TellerEnrollResponse:
    """Store a new Teller enrollment and return available accounts."""
    # -- Token signing verification (skip if key not configured) --------
    signing_key = settings.teller_token_signing_key
    if signing_key:
        if not body.nonce or not body.nonce_mac:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Token signing verification requires nonce and nonce_mac.",
            )
        if not verify_nonce_mac(body.nonce, body.nonce_mac, settings.jwt_secret):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Invalid or expired enrollment nonce.",
            )
        if not verify_token_signatures(
            access_token=body.access_token,
            nonce=body.nonce,
            teller_user_id=body.teller_user_id,
            enrollment_id=body.enrollment_id,
            environment=settings.teller_environment,
            signatures=body.signatures,
            public_key_b64=signing_key,
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Enrollment signature verification failed.",
            )

    existing = await teller_repository.get_active_enrollment(db, user_id)
    if existing is not None:
        await teller_repository.mark_disconnected(db, existing.id)

    encrypted_token = encrypt_token(body.access_token, settings.teller_encryption_key)

    enrollment = await teller_repository.create_enrollment(
        db,
        user_id=user_id,
        enrollment_id=body.enrollment_id,
        institution_name=body.institution,
        access_token_encrypted=encrypted_token,
    )
    try:
        await db.commit()
    except DBIntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An enrollment is already in progress. Please complete or cancel it first.",
        )

    cert_path: str = request.app.state.teller_cert_path
    key_path: str = request.app.state.teller_key_path

    try:
        async with build_teller_client(cert_path, key_path, body.access_token) as client:
            accounts = await fetch_accounts(client)
    except TellerApiError as exc:
        logger.error("Failed to fetch accounts for enrollment %s: %s", enrollment.id, exc.detail)
        await teller_repository.update_status(db, enrollment.id, TellerStatus.ERROR)
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not fetch accounts from your bank. Please try again.",
        ) from exc

    if not accounts:
        await teller_repository.update_status(db, enrollment.id, TellerStatus.ERROR)
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No accounts were returned by your bank.",
        )

    account_options = [
        TellerAccountOption(
            id=a.id,
            name=a.name,
            type=a.type,
            subtype=a.subtype,
            currency=a.currency,
            institution_name=a.institution.name,
        )
        for a in accounts
    ]

    return TellerEnrollResponse(
        status=TellerStatus.AWAITING_ACCOUNT,
        institution_name=enrollment.institution_name,
        accounts=account_options,
    )


# ---------------------------------------------------------------------------
# POST /teller/select-account
# ---------------------------------------------------------------------------


@router.post("/select-account")
async def select_account(
    body: TellerSelectAccountRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TellerStatusResponse:
    """Confirm the user's account choice and kick off initial data sync.

    Returns immediately; frontend polls GET /status for progress.
    """
    enrollment = await teller_repository.get_active_enrollment(db, user_id)
    if enrollment is None or enrollment.status != TellerStatus.AWAITING_ACCOUNT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No enrollment awaiting account selection",
        )

    access_token = decrypt_token(
        enrollment.access_token_encrypted, settings.teller_encryption_key
    )
    cert_path: str = request.app.state.teller_cert_path
    key_path: str = request.app.state.teller_key_path

    try:
        async with build_teller_client(cert_path, key_path, access_token) as client:
            accounts = await fetch_accounts(client)
    except TellerApiError as exc:
        logger.error(
            "Failed to verify account selection for enrollment %s: %s",
            enrollment.id,
            exc.detail,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not verify account with your bank. Please try again.",
        ) from exc

    selected = next((a for a in accounts if a.id == body.account_id), None)
    if selected is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Selected account not found. It may have been closed.",
        )

    transitioned = await teller_repository.transition_status(
        db, enrollment.id, TellerStatus.AWAITING_ACCOUNT, TellerStatus.SYNCING
    )
    if not transitioned:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Account selection already in progress.",
        )

    await teller_repository.update_account_details(
        db,
        enrollment_id=enrollment.id,
        account_id=selected.id,
        account_name=selected.name,
        account_currency=selected.currency,
    )
    await db.commit()

    factory: async_sessionmaker[AsyncSession] = request.app.state.db_session_factory
    ctx = _SyncContext(
        factory=factory,
        enrollment_id=enrollment.id,
        teller_enrollment_id=enrollment.enrollment_id,
        access_token=access_token,
        cert_path=cert_path,
        key_path=key_path,
        user_id=user_id,
        account_id=selected.id,
        account_name=selected.name,
        account_currency=selected.currency,
    )
    task = asyncio.create_task(_initial_sync(ctx))
    sync_tasks: dict[int, asyncio.Task[None]] = request.app.state.teller_sync_tasks
    sync_tasks[enrollment.id] = task
    task.add_done_callback(lambda _: sync_tasks.pop(enrollment.id, None))

    return TellerStatusResponse(
        is_connected=True,
        institution_name=enrollment.institution_name,
        account_name=selected.name,
        last_synced_at=None,
        status=TellerStatus.SYNCING,
    )


# ---------------------------------------------------------------------------
# GET /teller/status
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_status(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TellerStatusResponse:
    """Return the current Teller connection state for the user."""
    enrollment = await teller_repository.get_active_enrollment(db, user_id)
    if enrollment is None:
        return TellerStatusResponse(
            is_connected=False,
            institution_name=None,
            account_name=None,
            last_synced_at=None,
            status=TellerStatus.DISCONNECTED,
        )

    return TellerStatusResponse(
        is_connected=enrollment.status in (TellerStatus.ACTIVE, TellerStatus.SYNCING),
        institution_name=enrollment.institution_name,
        account_name=enrollment.account_name,
        last_synced_at=enrollment.last_synced_at,
        status=enrollment.status,
    )


# ---------------------------------------------------------------------------
# DELETE /teller/disconnect
# ---------------------------------------------------------------------------


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Disconnect the user's Teller enrollment."""
    enrollment = await teller_repository.get_active_enrollment(db, user_id)
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active enrollment")

    # Cancel any in-flight background sync for this enrollment.
    sync_tasks: dict[int, asyncio.Task[None]] = request.app.state.teller_sync_tasks
    in_flight = sync_tasks.pop(enrollment.id, None)
    if in_flight and not in_flight.done():
        in_flight.cancel()

    # Best-effort API revocation (don't fail if Teller is unreachable).
    if enrollment.account_id:
        try:
            token = decrypt_token(
                enrollment.access_token_encrypted, settings.teller_encryption_key
            )
            cert_path: str = request.app.state.teller_cert_path
            key_path: str = request.app.state.teller_key_path
            async with build_teller_client(cert_path, key_path, token) as client:
                await delete_enrollment(client, enrollment.account_id)
        except TellerApiError:
            logger.warning(
                "Teller API revocation failed for enrollment %s — marking disconnected anyway",
                enrollment.id,
            )

    await teller_repository.mark_disconnected(db, enrollment.id)
    await db.commit()


# ---------------------------------------------------------------------------
# POST /teller/webhook
# ---------------------------------------------------------------------------


@router.post("/webhook")
async def webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Ingest Teller webhook events.

    Always returns 200 to prevent Teller retry storms.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-teller-signature", "")

    if not verify_webhook_signature(raw_body, signature, settings.teller_webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        logger.warning("Webhook received malformed JSON payload")
        return {"status": "ok"}

    event_type: str = payload.get("type", "")

    factory: async_sessionmaker[AsyncSession] = request.app.state.db_session_factory

    async with factory() as db:
        if event_type == "enrollment.disconnected":
            await _handle_enrollment_disconnected(db, payload)
        elif event_type == "transactions.processed":
            await _handle_transactions_processed(db, payload, settings)
        else:
            logger.info("Ignoring unknown Teller webhook event: %s", event_type)

        await db.commit()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Webhook event handlers
# ---------------------------------------------------------------------------


async def _handle_enrollment_disconnected(
    db: AsyncSession,
    payload: dict,
) -> None:
    """Mark the enrollment as disconnected when Teller notifies us."""
    enrollment_id = payload.get("payload", {}).get("enrollment_id", "")
    if not enrollment_id:
        logger.warning("enrollment.disconnected webhook missing enrollment_id")
        return

    enrollment = await teller_repository.get_enrollment_by_enrollment_id(db, enrollment_id)
    if enrollment is None:
        logger.warning(
            "enrollment.disconnected webhook for unknown enrollment: %s", enrollment_id
        )
        return

    await teller_repository.mark_disconnected(db, enrollment.id)
    logger.info("Enrollment %s marked disconnected via webhook", enrollment_id)


async def _handle_transactions_processed(
    db: AsyncSession,
    payload: dict,
    settings: Settings,
) -> None:
    """Ingest new transactions from a Teller webhook."""
    account_id = payload.get("payload", {}).get("account_id", "")
    if not account_id:
        logger.warning("transactions.processed webhook missing account_id")
        return

    enrollment = await teller_repository.get_enrollment_by_account(db, account_id)
    if enrollment is None:
        logger.warning(
            "transactions.processed webhook for unknown account: %s", account_id
        )
        return

    transactions = payload.get("payload", {}).get("transactions", [])
    if not transactions:
        logger.info("transactions.processed webhook with empty transaction list")
        return

    teller_currency = enrollment.account_currency
    user_currency = await get_user_account_currency(enrollment.user_id, db)

    for txn in transactions:
        teller_txn_id = txn.get("id", "")
        if not teller_txn_id:
            logger.warning("Skipping transaction with empty id in webhook")
            continue

        raw_amount = txn.get("amount", "0")
        try:
            # Teller: negative = debit. Our DB: positive = money spent.
            amount = abs(Decimal(raw_amount).quantize(Decimal("0.01")))
        except (InvalidOperation, ValueError):
            logger.warning("Skipping transaction with invalid amount: %s", raw_amount)
            continue

        amount = await convert_amount(amount, teller_currency, user_currency)

        date_str = txn.get("date", "")
        try:
            purchase_date = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            purchase_date = datetime.now(UTC)

        await transaction_repository.create_from_teller(
            db,
            user_id=enrollment.user_id,
            amount=amount,
            purchase_date=purchase_date,
            teller_transaction_id=teller_txn_id,
            merchant=txn.get("description"),
            category=txn.get("category"),
        )


# ---------------------------------------------------------------------------
# Background initial sync
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class _SyncContext:
    """Immutable bundle of values needed by _initial_sync."""

    factory: async_sessionmaker[AsyncSession]
    enrollment_id: int
    teller_enrollment_id: str
    access_token: str
    cert_path: str
    key_path: str
    user_id: int
    account_id: str
    account_name: str
    account_currency: str


async def _initial_sync(ctx: _SyncContext) -> None:
    """Background task that runs after POST /select-account returns.

    Fetches current balance and recent transactions for the user-selected
    account, then transitions enrollment to 'active'.
    On failure, transitions to 'error'.
    """
    try:
        async with build_teller_client(ctx.cert_path, ctx.key_path, ctx.access_token) as client:
            balance_data = await fetch_balances(client, ctx.account_id)
            now = datetime.now(UTC)

            try:
                raw_balance = Decimal(balance_data.available).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                raw_balance = Decimal("0.00")

            teller_transactions = await fetch_transactions(client, ctx.account_id)

        # All Teller API work is done. Write balance + transactions atomically.
        async with ctx.factory() as db:
            user_currency = await get_user_account_currency(ctx.user_id, db)

            converted_balance = await convert_amount(
                raw_balance, ctx.account_currency, user_currency
            )

            await balance_repository.create_from_teller(
                db,
                user_id=ctx.user_id,
                balance=converted_balance,
                observed_at=now,
                account_label=ctx.account_name,
            )

            for txn in teller_transactions:
                try:
                    amount = abs(Decimal(txn.amount).quantize(Decimal("0.01")))
                except (InvalidOperation, ValueError):
                    continue

                amount = await convert_amount(amount, ctx.account_currency, user_currency)

                try:
                    purchase_date = datetime.fromisoformat(txn.date).replace(
                        tzinfo=UTC
                    )
                except (ValueError, TypeError):
                    purchase_date = now

                await transaction_repository.create_from_teller(
                    db,
                    user_id=ctx.user_id,
                    amount=amount,
                    purchase_date=purchase_date,
                    teller_transaction_id=txn.id,
                    merchant=txn.description,
                    category=txn.category,
                )
            await db.commit()

        async with ctx.factory() as db:
            activated = await teller_repository.transition_status(
                db, ctx.enrollment_id, TellerStatus.SYNCING, TellerStatus.ACTIVE
            )
            if activated:
                await teller_repository.update_last_synced(db, ctx.enrollment_id)
            else:
                logger.info(
                    "Enrollment %s status changed during sync (likely disconnected), "
                    "skipping activation",
                    ctx.teller_enrollment_id,
                )
            await db.commit()

        logger.info("Initial Teller sync complete for enrollment %s", ctx.teller_enrollment_id)

    except asyncio.CancelledError:
        logger.info(
            "Initial sync cancelled for enrollment %s (user disconnected)",
            ctx.teller_enrollment_id,
        )
        raise

    except TellerApiError as exc:
        logger.exception(
            "Teller API error during initial sync (enrollment %s): %s",
            ctx.teller_enrollment_id,
            exc.detail,
        )
        target = TellerStatus.DISCONNECTED if exc.status_code in (401, 403) else TellerStatus.ERROR
        async with ctx.factory() as db:
            await teller_repository.transition_status(
                db, ctx.enrollment_id, TellerStatus.SYNCING, target
            )
            await db.commit()

    except Exception:
        logger.exception(
            "Unexpected error during initial sync for enrollment %s",
            ctx.teller_enrollment_id,
        )
        async with ctx.factory() as db:
            await teller_repository.transition_status(
                db, ctx.enrollment_id, TellerStatus.SYNCING, TellerStatus.ERROR
            )
            await db.commit()
