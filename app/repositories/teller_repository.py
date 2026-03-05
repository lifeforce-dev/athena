"""Data access layer for Teller enrollments."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import TellerEnrollment


async def create_enrollment(
    db: AsyncSession,
    user_id: int,
    enrollment_id: str,
    institution_name: str,
    access_token_encrypted: str,
    account_id: str | None = None,
    account_name: str | None = None,
    account_currency: str = "USD",
) -> TellerEnrollment:
    """Insert a new Teller enrollment.

    The partial unique index (uq_teller_user_active) prevents duplicate
    active/syncing enrollments. Callers should disconnect old enrollments
    before creating a new one.
    """
    enrollment = TellerEnrollment(
        user_id=user_id,
        enrollment_id=enrollment_id,
        institution_name=institution_name,
        access_token_encrypted=access_token_encrypted,
        account_id=account_id,
        account_name=account_name,
        account_currency=account_currency,
    )
    db.add(enrollment)
    await db.flush()
    await db.refresh(enrollment)
    return enrollment


async def get_active_enrollment(
    db: AsyncSession,
    user_id: int,
) -> TellerEnrollment | None:
    """Return the single active or syncing enrollment for a user."""
    result = await db.execute(
        select(TellerEnrollment)
        .where(
            TellerEnrollment.user_id == user_id,
            TellerEnrollment.status.in_(["active", "syncing"]),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_enrollment_by_account(
    db: AsyncSession,
    account_id: str,
) -> TellerEnrollment | None:
    """Look up an enrollment by its Teller account ID.

    Used by the webhook handler to resolve incoming events.
    """
    result = await db.execute(
        select(TellerEnrollment).where(
            TellerEnrollment.account_id == account_id,
            TellerEnrollment.status.in_(["active", "syncing"]),
        )
    )
    return result.scalar_one_or_none()


async def get_enrollment_by_enrollment_id(
    db: AsyncSession,
    enrollment_id: str,
) -> TellerEnrollment | None:
    """Look up an enrollment by its Teller enrollment ID.

    Used by webhook events that reference enrollment_id rather than account_id.
    """
    result = await db.execute(
        select(TellerEnrollment).where(
            TellerEnrollment.enrollment_id == enrollment_id,
        )
    )
    return result.scalar_one_or_none()


async def get_all_active(db: AsyncSession) -> list[TellerEnrollment]:
    """Return all enrollments with status 'active' (for daily sync)."""
    result = await db.execute(
        select(TellerEnrollment).where(TellerEnrollment.status == "active")
    )
    return list(result.scalars().all())


async def update_status(
    db: AsyncSession,
    enrollment_id: int,
    status: str,
) -> None:
    """Set the enrollment status (active, disconnected, error)."""
    await db.execute(
        update(TellerEnrollment)
        .where(TellerEnrollment.id == enrollment_id)
        .values(status=status, updated_at=datetime.now(timezone.utc))
    )


async def update_account_details(
    db: AsyncSession,
    enrollment_id: int,
    account_id: str,
    account_name: str,
    account_currency: str,
) -> None:
    """Populate account details after the initial sync resolves the account."""
    await db.execute(
        update(TellerEnrollment)
        .where(TellerEnrollment.id == enrollment_id)
        .values(
            account_id=account_id,
            account_name=account_name,
            account_currency=account_currency,
            updated_at=datetime.now(timezone.utc),
        )
    )


async def update_last_synced(
    db: AsyncSession,
    enrollment_id: int,
) -> None:
    """Stamp the last_synced_at timestamp after a successful sync."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(TellerEnrollment)
        .where(TellerEnrollment.id == enrollment_id)
        .values(last_synced_at=now, updated_at=now)
    )


async def mark_disconnected(
    db: AsyncSession,
    enrollment_id: int,
) -> None:
    """Mark an enrollment as disconnected (token revoked or user action)."""
    await update_status(db, enrollment_id, "disconnected")
