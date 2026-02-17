"""Business logic for commitment management."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment_schemas import CommitmentCreate, CommitmentUpdate
from app.models.orm import Commitment
from app.repositories import commitment_repository as repo


# Frequency -> required field(s) mapping for merged-state validation.
_FREQUENCY_REQUIRED_FIELDS: dict[str, list[str]] = {
    "daily": ["anchor_date"],
    "weekly": ["anchor_date"],
    "biweekly": ["anchor_date"],
    "monthly": ["day_of_month"],
    "once": ["one_time_date"],
}


def _validate_merged_state(frequency: str, merged: dict[str, object]) -> None:
    """Ensure the merged commitment state has valid frequency-specific fields.

    Raises HTTPException 422 if required fields are missing for the frequency.
    """
    required = _FREQUENCY_REQUIRED_FIELDS.get(frequency, [])
    missing = [f for f in required if not merged.get(f)]

    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{', '.join(missing)} required for '{frequency}' frequency",
        )


async def list_commitments(db: AsyncSession, user_id: int) -> list[Commitment]:
    """Return all active commitments for a user."""
    return await repo.list_active(db, user_id)


async def get_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
) -> Commitment | None:
    """Get a single commitment by ID, scoped to user."""
    return await repo.get_by_id(db, commitment_id, user_id)


async def create_commitment(
    db: AsyncSession,
    user_id: int,
    data: CommitmentCreate,
) -> Commitment:
    """Create a new commitment from validated request data."""
    return await repo.create(db, user_id, **data.model_dump())


async def update_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
    data: CommitmentUpdate,
) -> Commitment | None:
    """Update a commitment with only the provided fields.

    Validates that the merged result (existing + delta) still has all
    required frequency-specific fields before persisting.
    """
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await repo.get_by_id(db, commitment_id, user_id)

    existing = await repo.get_by_id(db, commitment_id, user_id)
    if existing is None:
        return None

    # Build merged view: existing column values overridden by update fields.
    merged: dict[str, object] = {
        "frequency": existing.frequency,
        "day_of_month": existing.day_of_month,
        "anchor_date": existing.anchor_date,
        "one_time_date": existing.one_time_date,
    }
    merged.update(fields)
    _validate_merged_state(str(merged["frequency"]), merged)

    return await repo.update_by_id(db, commitment_id, user_id, **fields)


async def delete_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
) -> bool:
    """Soft-delete a commitment. Returns True if found and deactivated."""
    return await repo.soft_delete(db, commitment_id, user_id)
