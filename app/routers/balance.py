"""Balance snapshot endpoints: current, history, and manual entry."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.balance_schemas import (
    BalanceSnapshotResponse,
    ManualBalanceCreate,
)
from app.repositories import balance_repository as repo
from app.services.currency_service import get_user_currencies, to_account_currency

router = APIRouter(prefix="/balance", tags=["balance"])


@router.get("/current", response_model=BalanceSnapshotResponse | None)
async def get_current_balance(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BalanceSnapshotResponse | None:
    """Return the most recent balance snapshot, or null if none exist."""
    row = await repo.get_latest(db, user_id)
    if row is None:
        return None
    return BalanceSnapshotResponse.model_validate(row)


@router.get("/history", response_model=list[BalanceSnapshotResponse])
async def get_balance_history(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[BalanceSnapshotResponse]:
    """Return recent balance snapshots, newest first."""
    rows = await repo.list_history(db, user_id, limit=limit)
    return [BalanceSnapshotResponse.model_validate(row) for row in rows]


@router.post("/manual", response_model=BalanceSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_balance(
    data: ManualBalanceCreate,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BalanceSnapshotResponse:
    """Manually record a balance snapshot."""
    info = await get_user_currencies(user_id, db)
    data.balance = await to_account_currency(data.balance, info)
    row = await repo.create_manual(
        db,
        user_id,
        balance=data.balance,
        observed_at=data.observed_at,
        account_label=data.account_label,
    )
    await db.commit()
    return BalanceSnapshotResponse.model_validate(row)
