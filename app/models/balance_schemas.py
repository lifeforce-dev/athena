"""Pydantic models for balance and transaction API responses."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BalanceSnapshotResponse(BaseModel):
    """API response for a single balance snapshot."""

    id: int
    balance: Decimal
    account_label: str | None
    observed_at: datetime
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualBalanceCreate(BaseModel):
    """Request body for manually recording a balance snapshot."""

    balance: Decimal
    observed_at: datetime
    account_label: str | None = Field(default=None, max_length=64)


class TransactionResponse(BaseModel):
    """API response for a single transaction."""

    id: int
    amount: Decimal
    merchant: str | None
    card_last_four: str | None
    purchase_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
