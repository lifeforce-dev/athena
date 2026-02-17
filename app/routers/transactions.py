"""Transaction list endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.balance_schemas import TransactionResponse
from app.repositories import transaction_repository as repo

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _user_id(user: dict) -> int:
    return int(user["sub"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[TransactionResponse]:
    """Return recent bank transactions, newest first."""
    rows = await repo.list_recent(db, _user_id(user), limit=limit)
    return [TransactionResponse.model_validate(row) for row in rows]
