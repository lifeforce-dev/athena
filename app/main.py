from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.logging import setup_logging
from app.config import get_settings
from app.routers.projection import router as projection_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Initialize logging at startup."""
    setup_logging()
    logger.info('Athena API initialized')
    yield


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware and routes."""
    settings = get_settings()

    application = FastAPI(title='Athena - Cash Projection API', version='0.1.0', lifespan=lifespan)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['*'],
    )

    application.include_router(projection_router, prefix='/api')

    @application.get('/health')
    async def health_check() -> dict[str, str]:
        return {'status': 'ok'}

    return application


app = create_app()
