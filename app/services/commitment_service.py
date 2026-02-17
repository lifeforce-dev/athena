"""Business logic for commitment management."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commitment_schemas import CommitmentCreate, CommitmentUpdate
from app.models.orm import Commitment
from app.repositories import commitment_repository as repo


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
    """Update a commitment with only the provided fields."""
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await repo.get_by_id(db, commitment_id, user_id)

    return await repo.update_by_id(db, commitment_id, user_id, **fields)


async def delete_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
) -> bool:
    """Soft-delete a commitment. Returns True if found and deactivated."""
    return await repo.soft_delete(db, commitment_id, user_id)
