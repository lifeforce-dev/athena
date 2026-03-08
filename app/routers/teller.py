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
from app.models.orm import TellerEnrollment
from app.models.teller_constants import TellerStatus
from app.models.teller_schemas import (
    RefreshBalanceResponse,
    TellerAccount,
    TellerAccountOption,
    TellerEnrollRequest,
    TellerEnrollResponse,
    TellerNonceResponse,
    TellerSelectAccountRequest,
    TellerStatusResponse,
)
from app.repositories import balance_repository, teller_repository, transaction_repository
from app.services.currency_service import (
    CurrencyConversionError,
    convert_amount,
    get_user_account_currency,
)
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


def _verify_enrollment_tokens(body: TellerEnrollRequest, settings: Settings) -> None:
    """Validate nonce freshness and Ed25519 token signatures.

    No-op when the token signing key is not configured (dev environments).
    Raises HTTPException on any verification failure.
    """
    signing_key = settings.teller_token_signing_key
    if not signing_key:
        return

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


_ALLOWED_ACCOUNT_TYPES = frozenset({"depository"})


async def _fetch_eligible_accounts(
    enrollment_id: int,
    cert_path: str,
    key_path: str,
    access_token: str,
    db: AsyncSession,
) -> list[TellerAccount]:
    """Fetch accounts from Teller and return only depository types.

    Marks the enrollment as ERROR and raises HTTPException when Teller
    returns no accounts or none of the supported type.
    """
    try:
        async with build_teller_client(cert_path, key_path, access_token) as client:
            accounts = await fetch_accounts(client)
    except TellerApiError as exc:
        logger.error("Failed to fetch accounts for enrollment %s: %s", enrollment_id, exc.detail)
        await teller_repository.update_status(db, enrollment_id, TellerStatus.ERROR)
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not fetch accounts from your bank. Please try again.",
        ) from exc

    if not accounts:
        await teller_repository.update_status(db, enrollment_id, TellerStatus.ERROR)
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No accounts were returned by your bank.",
        )

    eligible = [a for a in accounts if a.type in _ALLOWED_ACCOUNT_TYPES]
    if not eligible:
        await teller_repository.update_status(db, enrollment_id, TellerStatus.ERROR)
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No supported checking or savings accounts found at your bank.",
        )

    return eligible


async def _verify_account_selection(
    enrollment_id: int,
    account_id: str,
    cert_path: str,
    key_path: str,
    access_token: str,
) -> TellerAccount:
    """Fetch accounts from Teller and validate the user's selection.

    Raises HTTPException if the account doesn't exist or isn't depository.
    """
    try:
        async with build_teller_client(cert_path, key_path, access_token) as client:
            accounts = await fetch_accounts(client)
    except TellerApiError as exc:
        logger.error(
            "Failed to verify account selection for enrollment %s: %s",
            enrollment_id,
            exc.detail,
        )
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not verify account with your bank. Please try again.",
        ) from exc

    selected = next((a for a in accounts if a.id == account_id), None)
    if selected is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Selected account not found. It may have been closed.",
        )

    if selected.type != "depository":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only checking and savings accounts are supported.",
        )

    return selected


def _launch_initial_sync(
    *,
    request: Request,
    enrollment: TellerEnrollment,
    access_token: str,
    cert_path: str,
    key_path: str,
    user_id: int,
    selected: TellerAccount,
) -> None:
    """Create the background sync task and register it for cancellation."""
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


@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll(
    body: TellerEnrollRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TellerEnrollResponse:
    """Store a new Teller enrollment and return available accounts."""
    _verify_enrollment_tokens(body, settings)

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
    except DBIntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An enrollment is already in progress. Please complete or cancel it first.",
        ) from exc

    cert_path: str = request.app.state.teller_cert_path
    key_path: str = request.app.state.teller_key_path
    eligible = await _fetch_eligible_accounts(
        enrollment.id, cert_path, key_path, body.access_token, db
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
        for a in eligible
    ]

    return TellerEnrollResponse(
        status=TellerStatus.AWAITING_ACCOUNT,
        institution_name=enrollment.institution_name,
        accounts=account_options,
    )


@router.get("/accounts")
async def get_pending_accounts(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TellerEnrollResponse:
    """Re-fetch selectable accounts for an enrollment awaiting account choice.

    Used after a page reload to restore the account picker when the
    enrollment is in AWAITING_ACCOUNT but the client lost the list.
    """
    enrollment = await teller_repository.get_active_enrollment(db, user_id)
    if enrollment is None or enrollment.status != TellerStatus.AWAITING_ACCOUNT:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No enrollment awaiting account selection.",
        )

    access_token = decrypt_token(
        enrollment.access_token_encrypted, settings.teller_encryption_key
    )
    cert_path: str = request.app.state.teller_cert_path
    key_path: str = request.app.state.teller_key_path

    eligible = await _fetch_eligible_accounts(
        enrollment.id, cert_path, key_path, access_token, db
    )

    return TellerEnrollResponse(
        status=TellerStatus.AWAITING_ACCOUNT,
        institution_name=enrollment.institution_name,
        accounts=[
            TellerAccountOption(
                id=a.id,
                name=a.name,
                type=a.type,
                subtype=a.subtype,
                currency=a.currency,
                institution_name=a.institution.name,
            )
            for a in eligible
        ],
    )


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

    selected = await _verify_account_selection(
        enrollment.id, body.account_id, cert_path, key_path, access_token
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

    _launch_initial_sync(
        request=request,
        enrollment=enrollment,
        access_token=access_token,
        cert_path=cert_path,
        key_path=key_path,
        user_id=user_id,
        selected=selected,
    )

    return TellerStatusResponse(
        is_connected=True,
        institution_name=enrollment.institution_name,
        account_name=selected.name,
        last_synced_at=None,
        status=TellerStatus.SYNCING,
    )


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
            last_manual_refresh_at=None,
            status=TellerStatus.DISCONNECTED,
        )

    return TellerStatusResponse(
        is_connected=enrollment.status in (TellerStatus.ACTIVE, TellerStatus.SYNCING),
        institution_name=enrollment.institution_name,
        account_name=enrollment.account_name,
        last_synced_at=enrollment.last_synced_at,
        last_manual_refresh_at=enrollment.last_manual_refresh_at,
        status=enrollment.status,
    )


# ── Manual balance refresh ────────────────────────────────────────────

MANUAL_REFRESH_COOLDOWN_SECONDS = 3600  # 1 hour


def _enforce_cooldown(enrollment: TellerEnrollment) -> None:
    """Raise 429 if the manual refresh cooldown has not elapsed."""
    if enrollment.last_manual_refresh_at is None:
        return
    elapsed = (datetime.now(UTC) - enrollment.last_manual_refresh_at).total_seconds()
    if elapsed >= MANUAL_REFRESH_COOLDOWN_SECONDS:
        return
    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "message": "Refresh on cooldown",
            "cooldown_started_at": enrollment.last_manual_refresh_at.isoformat(),
            "cooldown_seconds": MANUAL_REFRESH_COOLDOWN_SECONDS,
        },
    )


async def _fetch_and_store_balance(
    enrollment: TellerEnrollment,
    user_id: int,
    db: AsyncSession,
    cert_path: str,
    key_path: str,
    settings: Settings,
) -> Decimal:
    """Call Teller API for the latest balance, convert, and persist a snapshot.

    Returns the converted balance. Marks the enrollment disconnected if
    the token has been revoked.
    """
    token = decrypt_token(
        enrollment.access_token_encrypted, settings.teller_encryption_key
    )

    try:
        async with build_teller_client(cert_path, key_path, token) as client:
            balance_data = await fetch_balances(client, enrollment.account_id)  # type: ignore[arg-type]
    except TellerApiError as exc:
        if exc.status_code in (401, 403):
            await teller_repository.mark_disconnected(db, enrollment.id)
            await db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bank connection expired — please reconnect")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Teller API error: {exc.detail}")

    try:
        raw_balance = Decimal(balance_data.available).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raw_balance = Decimal("0.00")

    try:
        user_currency = await get_user_account_currency(user_id, db)
        converted = await convert_amount(raw_balance, enrollment.account_currency, user_currency)
    except CurrencyConversionError:
        converted = raw_balance

    now = datetime.now(UTC)
    await balance_repository.create_from_teller(
        db, user_id=user_id, balance=converted, observed_at=now, account_label=enrollment.account_name,
    )
    await teller_repository.update_last_synced(db, enrollment.id)
    return converted


@router.post("/refresh-balance", response_model=RefreshBalanceResponse)
async def refresh_balance(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RefreshBalanceResponse:
    """Manually refresh the balance from the user's connected bank account.

    Enforces a server-side cooldown of 1 hour. Returns the new balance
    and the cooldown start timestamp so the client can render a
    real-time countdown.
    """
    enrollment = await teller_repository.get_active_enrollment(db, user_id)
    if enrollment is None or enrollment.status != TellerStatus.ACTIVE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active bank connection")

    _enforce_cooldown(enrollment)

    cert_path: str = request.app.state.teller_cert_path
    key_path: str = request.app.state.teller_key_path
    converted_balance = await _fetch_and_store_balance(
        enrollment, user_id, db, cert_path, key_path, settings,
    )

    await teller_repository.update_last_manual_refresh(db, enrollment.id)
    await db.commit()

    return RefreshBalanceResponse(
        balance=str(converted_balance),
        cooldown_started_at=datetime.now(UTC).isoformat(),
        cooldown_seconds=MANUAL_REFRESH_COOLDOWN_SECONDS,
    )


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


@router.post("/webhook")
async def webhook(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Ingest Teller webhook events.

    Always returns 200 to prevent Teller retry storms.
    """
    raw_body = await request.body()
    signature = request.headers.get("teller-signature", "")

    if not verify_webhook_signature(raw_body, signature, settings.teller_webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")

    try:
        payload = await request.json()
    except ValueError:
        logger.warning("Webhook received malformed JSON payload")
        return {"status": "ok"}

    event_type: str = payload.get("type", "")

    factory: async_sessionmaker[AsyncSession] = request.app.state.db_session_factory
    cert_path: str = getattr(request.app.state, "teller_cert_path", "")
    key_path: str = getattr(request.app.state, "teller_key_path", "")

    try:
        async with factory() as db:
            if event_type == "enrollment.disconnected":
                await _handle_enrollment_disconnected(db, payload)
            elif event_type == "transactions.processed":
                await _handle_transactions_processed(
                    db, payload, settings, cert_path, key_path,
                )
            else:
                logger.info("Ignoring unknown Teller webhook event: %s", event_type)

            await db.commit()
    except CurrencyConversionError:
        logger.exception("FX conversion failed during webhook %s — event acknowledged", event_type)
    except Exception:
        logger.exception("Error processing webhook event %s — event acknowledged", event_type)

    return {"status": "ok"}


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
    cert_path: str,
    key_path: str,
) -> None:
    """Ingest new transactions from a Teller webhook and refresh the balance."""
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
        await _ingest_transaction(
            db,
            user_id=enrollment.user_id,
            txn_data=txn,
            teller_currency=teller_currency,
            user_currency=user_currency,
        )

    # Fetch fresh balance from Teller so the dashboard reflects the spend.
    await _refresh_balance_from_teller(
        db,
        enrollment=enrollment,
        settings=settings,
        cert_path=cert_path,
        key_path=key_path,
        user_currency=user_currency,
    )


async def _refresh_balance_from_teller(
    db: AsyncSession,
    *,
    enrollment: TellerEnrollment,
    settings: Settings,
    cert_path: str,
    key_path: str,
    user_currency: str,
) -> None:
    """Fetch current balance from Teller API and store a new snapshot.

    Called after ingesting webhook transactions so the user's dashboard
    balance stays current. Failures are logged but do not propagate —
    the transactions are already persisted, and the daily sync will
    reconcile the balance eventually.
    """
    if not cert_path or not key_path:
        logger.warning("Cannot refresh balance: mTLS cert paths not available")
        return

    try:
        token = decrypt_token(
            enrollment.access_token_encrypted, settings.teller_encryption_key
        )

        async with build_teller_client(cert_path, key_path, token) as client:
            balance_data = await fetch_balances(client, enrollment.account_id)  # type: ignore[arg-type]

        try:
            raw_balance = Decimal(balance_data.available).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            logger.warning("Invalid balance value from Teller: %s", balance_data.available)
            return

        converted_balance = await convert_amount(
            raw_balance, enrollment.account_currency, user_currency
        )

        now = datetime.now(UTC)
        await balance_repository.create_from_teller(
            db,
            user_id=enrollment.user_id,
            balance=converted_balance,
            observed_at=now,
            account_label=enrollment.account_name,
        )
        await teller_repository.update_last_synced(db, enrollment.id)
        logger.info(
            "Webhook balance refresh: stored %s %s for user %d",
            converted_balance, user_currency, enrollment.user_id,
        )

    except TellerApiError as exc:
        logger.warning(
            "Balance refresh failed for enrollment %s: %s", enrollment.id, exc.detail
        )
    except Exception:
        logger.exception("Unexpected error during webhook balance refresh")


async def _ingest_transaction(
    db: AsyncSession,
    *,
    user_id: int,
    txn_data: dict,
    teller_currency: str,
    user_currency: str,
    fallback_date: datetime | None = None,
) -> None:
    """Parse and store a single Teller transaction.

    Used by both the initial sync and webhook handler to avoid duplicating
    amount parsing, currency conversion, and date handling logic.
    """
    teller_txn_id = txn_data.get("id", "")
    if not teller_txn_id:
        logger.warning("Skipping transaction with empty id")
        return

    raw_amount = txn_data.get("amount", "0")
    try:
        # Teller: negative = debit.  Our DB: positive = money spent.
        amount = abs(Decimal(raw_amount).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        logger.warning("Skipping transaction with invalid amount: %s", raw_amount)
        return

    amount = await convert_amount(amount, teller_currency, user_currency)

    date_str = txn_data.get("date", "")
    try:
        purchase_date = datetime.fromisoformat(date_str).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        purchase_date = fallback_date or datetime.now(UTC)

    await transaction_repository.create_from_teller(
        db,
        user_id=user_id,
        amount=amount,
        purchase_date=purchase_date,
        teller_transaction_id=teller_txn_id,
        merchant=txn_data.get("description"),
        category=txn_data.get("category"),
    )


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

        await _persist_sync_data(ctx, raw_balance, teller_transactions, now)
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


async def _persist_sync_data(
    ctx: _SyncContext,
    raw_balance: Decimal,
    teller_transactions: list,
    observed_at: datetime,
) -> None:
    """Write balance, transactions, and status transition in one atomic commit.

    Keeps the DB work isolated from the Teller API calls so that a crash
    cannot strand the enrollment in 'syncing'.
    """
    async with ctx.factory() as db:
        user_currency = await get_user_account_currency(ctx.user_id, db)

        converted_balance = await convert_amount(
            raw_balance, ctx.account_currency, user_currency
        )

        await balance_repository.create_from_teller(
            db,
            user_id=ctx.user_id,
            balance=converted_balance,
            observed_at=observed_at,
            account_label=ctx.account_name,
        )

        for txn in teller_transactions:
            await _ingest_transaction(
                db,
                user_id=ctx.user_id,
                txn_data={
                    "id": txn.id,
                    "amount": txn.amount,
                    "date": txn.date,
                    "description": txn.description,
                    "category": txn.category,
                },
                teller_currency=ctx.account_currency,
                user_currency=user_currency,
                fallback_date=observed_at,
            )

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
