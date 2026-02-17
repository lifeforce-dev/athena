from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.logging import setup_logging
from app.config import get_settings
from app.database import build_engine, build_session_factory
from app.routers.auth import router as auth_router
from app.routers.commitments import router as commitments_router
from app.routers.projection import router as projection_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize logging and database at startup, clean up on shutdown."""
    setup_logging()

    settings = get_settings()

    engine = None
    if settings.database_url:
        engine = build_engine(settings.database_url)
        application.state.db_session_factory = build_session_factory(engine)
        logger.info("Database engine initialized")

    logger.info("Athena API initialized")
    yield

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

    application = FastAPI(title='Athena - Cash Projection API', version='0.1.0', lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['*'],
    )

    application.include_router(auth_router, prefix='/api')
    application.include_router(commitments_router, prefix='/api')
    application.include_router(projection_router, prefix='/api')

    @application.get('/health')
    async def health_check() -> dict[str, str]:
        return {'status': 'ok'}

    return application


app = create_app()
