"""CRUD endpoints for user commitments."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.commitment_schemas import (
    CommitmentCreate,
    CommitmentResponse,
    CommitmentUpdate,
)
from app.services import commitment_service as service

router = APIRouter(prefix="/commitments", tags=["commitments"])


@router.get("", response_model=list[CommitmentResponse])
async def list_commitments(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CommitmentResponse]:
    """List all active commitments for the authenticated user."""
    rows = await service.list_commitments(db, user_id)
    return [CommitmentResponse.model_validate(row) for row in rows]


@router.post("", response_model=CommitmentResponse, status_code=status.HTTP_201_CREATED)
async def create_commitment(
    data: CommitmentCreate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommitmentResponse:
    """Create a new commitment."""
    row = await service.create_commitment(db, user_id, data)
    await db.commit()
    return CommitmentResponse.model_validate(row)


@router.put("/{commitment_id}", response_model=CommitmentResponse)
async def update_commitment(
    commitment_id: int,
    data: CommitmentUpdate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommitmentResponse:
    """Update an existing commitment."""
    try:
        row = await service.update_commitment(db, commitment_id, user_id, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found")
    await db.commit()
    return CommitmentResponse.model_validate(row)


@router.delete("/{commitment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_commitment(
    commitment_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft-delete a commitment (sets is_active=False)."""
    found = await service.delete_commitment(db, commitment_id, user_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found")
    await db.commit()
