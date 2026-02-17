"""Async database engine and session management for PostgreSQL."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def build_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine from a PostgreSQL URL.

    Handles the common Render gotcha: Render provides ``postgresql://``
    but asyncpg requires ``postgresql+asyncpg://``.
    """
    url = database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(url, echo=False, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async DB session per request."""
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "db_session_factory", None
    )

    if factory is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )

    async with factory() as session:
        yield session
