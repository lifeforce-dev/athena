"""Balance snapshot endpoints: current, history, and manual entry."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.balance_schemas import (
    BalanceSnapshotResponse,
    ManualBalanceCreate,
)
from app.repositories import balance_repository as repo

router = APIRouter(prefix="/balance", tags=["balance"])


def _user_id(user: dict) -> int:
    return int(user["sub"])


@router.get("/current", response_model=BalanceSnapshotResponse | None)
async def get_current_balance(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BalanceSnapshotResponse | None:
    """Return the most recent balance snapshot, or null if none exist."""
    row = await repo.get_latest(db, _user_id(user))
    if row is None:
        return None
    return BalanceSnapshotResponse.model_validate(row)


@router.get("/history", response_model=list[BalanceSnapshotResponse])
async def get_balance_history(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[BalanceSnapshotResponse]:
    """Return recent balance snapshots, newest first."""
    rows = await repo.list_history(db, _user_id(user), limit=limit)
    return [BalanceSnapshotResponse.model_validate(row) for row in rows]


@router.post("/manual", response_model=BalanceSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_balance(
    data: ManualBalanceCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BalanceSnapshotResponse:
    """Manually record a balance snapshot."""
    row = await repo.create_manual(
        db,
        _user_id(user),
        balance=data.balance,
        observed_at=data.observed_at,
        account_label=data.account_label,
    )
    return BalanceSnapshotResponse.model_validate(row)
