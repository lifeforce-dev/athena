from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from importlib.metadata import entry_points

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.common.logging import setup_logging
from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory
from app.repositories import gmail_repository
from app.routers.auth import router as auth_router
from app.routers.balance import router as balance_router
from app.routers.commitments import router as commitments_router
from app.routers.currency import router as currency_router
from app.routers.demo import router as demo_router
from app.routers.demo_data import router as demo_data_router
from app.routers.gmail import router as gmail_router
from app.routers.notifications import router as notifications_router
from app.routers.projection import router as projection_router
from app.routers.teller import router as teller_router
from app.routers.transactions import router as transactions_router
from app.services.gmail_service import (
    parse_watch_expiry,
    register_watch,
    watch_needs_renewal,
)

logger = logging.getLogger(__name__)


# -- Gmail watch renewal ---------------------------------------------------


async def _maybe_renew_gmail_watch(
    factory: async_sessionmaker[AsyncSession], settings: Settings
) -> None:
    """Renew any Gmail watches expiring within 24 hours.

    Single-user system: iterates all rows (typically one). If multi-user
    support is added, filter by the configured Gmail address or add
    per-user credential storage.
    """
    async with factory() as db:
        subs = await gmail_repository.get_all(db)
        for sub in subs:
            if not watch_needs_renewal(sub.watch_expiry):
                continue

            logger.info(f"Renewing Gmail watch for {sub.gmail_address}")
            try:
                response = await register_watch(settings)
                sub.history_id = str(response["historyId"])
                sub.watch_expiry = parse_watch_expiry(response["expiration"])
                await db.commit()
                logger.info(f"Gmail watch renewed, expires {sub.watch_expiry}")
            except Exception:
                logger.exception("Gmail watch renewal failed")


async def _periodic_renewal_loop(
    factory: async_sessionmaker[AsyncSession], settings: Settings
) -> None:
    """Background task that checks and renews Gmail watches every 6 hours."""
    while True:
        await asyncio.sleep(6 * 3600)
        try:
            await _maybe_renew_gmail_watch(factory, settings)
        except Exception:
            logger.exception("Error in periodic Gmail watch renewal")


# -- Teller daily balance sync --------------------------------------------


async def _sync_teller_balances(
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    cert_path: str,
    key_path: str,
) -> None:
    """Fetch and store latest balance for all active Teller enrollments.

    Runs once per daily cycle. Each enrollment is handled independently so
    a single failure does not block the rest.
    """
    from datetime import datetime, timezone
    from decimal import Decimal, InvalidOperation

    from app.common.encryption import decrypt_token
    from app.repositories import balance_repository, teller_repository
    from app.services.currency_service import convert_amount, get_user_account_currency
    from app.services.teller_service import (
        TellerApiError,
        build_teller_client,
        fetch_balances,
    )

    async with factory() as db:
        enrollments = await teller_repository.get_all_active(db)

    for enrollment in enrollments:
        try:
            token = decrypt_token(
                enrollment.access_token_encrypted, settings.teller_encryption_key
            )

            async with build_teller_client(cert_path, key_path, token) as client:
                balance_data = await fetch_balances(client, enrollment.account_id)  # type: ignore[arg-type]

            try:
                raw_balance = Decimal(balance_data.available).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                raw_balance = Decimal("0.00")

            async with factory() as db:
                user_currency = await get_user_account_currency(enrollment.user_id, db)

            converted_balance = await convert_amount(
                raw_balance, enrollment.account_currency, user_currency
            )

            now = datetime.now(timezone.utc)
            async with factory() as db:
                await balance_repository.create_from_teller(
                    db,
                    user_id=enrollment.user_id,
                    balance=converted_balance,
                    observed_at=now,
                    account_label=enrollment.account_name,
                )
                await teller_repository.update_last_synced(db, enrollment.id)
                await db.commit()

            logger.info("Daily sync complete for enrollment %s", enrollment.id)

        except TellerApiError as exc:
            logger.warning(
                "Teller API error during daily sync (enrollment %s): %s",
                enrollment.id,
                exc.detail,
            )
            if exc.status_code in (401, 403):
                async with factory() as db:
                    await teller_repository.mark_disconnected(db, enrollment.id)
                    await db.commit()

        except Exception:
            logger.exception("Daily sync failed for enrollment %s", enrollment.id)


async def _periodic_teller_sync(
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    cert_path: str,
    key_path: str,
) -> None:
    """Background loop: sync Teller balances every 24 hours."""
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            await _sync_teller_balances(factory, settings, cert_path, key_path)
        except Exception:
            logger.exception("Error in periodic Teller balance sync")


# -- Application lifecycle -------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize logging, database, Gmail watch, and Teller sync at startup."""
    setup_logging()

    settings = get_settings()

    engine = None
    renewal_task = None
    teller_sync_task = None

    if settings.database_url:
        engine = build_engine(settings.database_url)
        application.state.db_session_factory = build_session_factory(engine)
        application.state.teller_sync_tasks = {}  # dict[int, asyncio.Task] keyed by enrollment ID
        logger.info("Database engine initialized")

        if settings.google_refresh_token:
            factory = application.state.db_session_factory
            try:
                await _maybe_renew_gmail_watch(factory, settings)
            except Exception:
                logger.exception("Gmail watch renewal on startup failed")

            renewal_task = asyncio.create_task(
                _periodic_renewal_loop(factory, settings)
            )

        if settings.teller_app_id and settings.teller_certificate_b64:
            from app.common.encryption import decode_cert_to_tempfile

            application.state.teller_cert_path = decode_cert_to_tempfile(
                settings.teller_certificate_b64
            )
            application.state.teller_key_path = decode_cert_to_tempfile(
                settings.teller_private_key_b64
            )
            logger.info("Teller mTLS certificates decoded to temp files")

            factory = application.state.db_session_factory
            teller_sync_task = asyncio.create_task(
                _periodic_teller_sync(
                    factory,
                    settings,
                    application.state.teller_cert_path,
                    application.state.teller_key_path,
                )
            )

    logger.info("Athena API initialized")
    yield

    if renewal_task is not None:
        renewal_task.cancel()
        with suppress(asyncio.CancelledError):
            await renewal_task

    if teller_sync_task is not None:
        teller_sync_task.cancel()
        with suppress(asyncio.CancelledError):
            await teller_sync_task

    # Cancel any in-flight per-enrollment sync tasks.
    sync_tasks: dict[int, asyncio.Task[None]] = getattr(
        application.state, "teller_sync_tasks", {}
    )
    for task in sync_tasks.values():
        task.cancel()
    for task in sync_tasks.values():
        with suppress(asyncio.CancelledError):
            await task

    for attr in ("teller_cert_path", "teller_key_path"):
        path = getattr(application.state, attr, None)
        if path:
            with suppress(OSError):
                os.unlink(path)
                logger.info("Removed temp cert file: %s", attr)

    if engine is not None:
        await engine.dispose()
        logger.info("Database engine disposed")


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware and routes."""
    settings = get_settings()

    if not settings.jwt_secret:
        raise RuntimeError(
            "ATHENA_JWT_SECRET is not set. Auth tokens cannot be signed securely."
        )

    if "*" in settings.cors_origins:
        raise RuntimeError(
            "CORS origins must not contain '*' when allow_credentials is enabled."
        )

    if settings.google_refresh_token and not settings.google_push_audience:
        raise RuntimeError(
            "ATHENA_GOOGLE_PUSH_AUDIENCE must be set when Gmail integration is enabled."
        )

    if settings.teller_app_id:
        if not settings.teller_certificate_b64:
            raise RuntimeError(
                "ATHENA_TELLER_CERTIFICATE_B64 required when Teller is enabled."
            )
        if not settings.teller_private_key_b64:
            raise RuntimeError(
                "ATHENA_TELLER_PRIVATE_KEY_B64 required when Teller is enabled."
            )
        if not settings.teller_encryption_key:
            raise RuntimeError(
                "ATHENA_TELLER_ENCRYPTION_KEY required when Teller is enabled."
            )
        if not settings.teller_webhook_secret:
            raise RuntimeError(
                "ATHENA_TELLER_WEBHOOK_SECRET required when Teller is enabled."
            )

    application = FastAPI(title='Athena - Cash Projection API', version='0.1.0', lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['*'],
    )

    application.include_router(auth_router, prefix='/api')
    application.include_router(balance_router, prefix='/api')
    application.include_router(commitments_router, prefix='/api')
    application.include_router(currency_router, prefix='/api')
    application.include_router(demo_router, prefix='/api')
    application.include_router(demo_data_router, prefix='/api')
    application.include_router(gmail_router, prefix='/api')
    application.include_router(notifications_router, prefix='/api')
    application.include_router(projection_router, prefix='/api')
    application.include_router(teller_router, prefix='/api')
    application.include_router(transactions_router, prefix='/api')

    # Discover and register plugin routers (e.g. athena-dev-tools).
    _register_plugins(application)

    @application.get('/health')
    async def health_check() -> dict[str, str]:
        return {'status': 'ok'}

    return application


def _register_plugins(application: FastAPI) -> None:
    """Load routers from installed packages that declare athena.plugins entry-points.

    Each entry-point must be a callable returning ``list[APIRouter]``.
    Packages that are not installed are simply absent -- no code, no routes.
    """
    discovered = entry_points(group="athena.plugins")

    for ep in discovered:
        try:
            get_routers = ep.load()
            routers: list[APIRouter] = get_routers()

            for plugin_router in routers:
                application.include_router(plugin_router, prefix='/api')

            logger.info(f"Plugin '{ep.name}' registered {len(routers)} router(s)")
        except Exception:
            logger.exception(f"Failed to load plugin '{ep.name}'")


app = create_app()
