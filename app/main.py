from __future__ import annotations

import asyncio
import logging
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


# -- Application lifecycle -------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize logging, database, and Gmail watch at startup."""
    setup_logging()

    settings = get_settings()

    engine = None
    renewal_task = None

    if settings.database_url:
        engine = build_engine(settings.database_url)
        application.state.db_session_factory = build_session_factory(engine)
        logger.info("Database engine initialized")

        # Renew Gmail watch on startup if credentials are configured.
        if settings.google_refresh_token:
            factory = application.state.db_session_factory
            try:
                await _maybe_renew_gmail_watch(factory, settings)
            except Exception:
                logger.exception("Gmail watch renewal on startup failed")

            renewal_task = asyncio.create_task(
                _periodic_renewal_loop(factory, settings)
            )

    logger.info("Athena API initialized")
    yield

    if renewal_task is not None:
        renewal_task.cancel()
        with suppress(asyncio.CancelledError):
            await renewal_task

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
        if not settings.teller_encryption_key:
            raise RuntimeError(
                "ATHENA_TELLER_ENCRYPTION_KEY required when Teller is enabled."
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
