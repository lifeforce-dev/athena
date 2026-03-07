"""Currency-related endpoints: set account currency, fetch exchange rates."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.orm import BalanceSnapshot, Commitment, User
from app.services.currency_service import get_rate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])

ALLOWED_CURRENCIES = {"USD", "KRW", "JPY", "EUR", "GBP", "CNY", "BRL"}

# Maps currency code to default locale for auto-setting account_language.
CURRENCY_DEFAULT_LANG: dict[str, str] = {
    "USD": "en_US",
    "KRW": "ko_KR",
    "JPY": "ja_JP",
    "EUR": "en_US",
    "GBP": "en_US",
    "CNY": "zh_CN",
    "BRL": "pt_BR",
}


# -- Models ----------------------------------------------------------------

class SetCurrencyRequest(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}")
        return upper


class SetCurrencyResponse(BaseModel):
    account_currency: str


class SetDisplayCurrencyRequest(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}")
        return upper


class SetDisplayCurrencyResponse(BaseModel):
    display_currency: str


class ExchangeRateResponse(BaseModel):
    base: str
    target: str
    rate: float


# -- Endpoints -------------------------------------------------------------

@router.patch("/account", response_model=SetCurrencyResponse)
async def set_account_currency(
    body: SetCurrencyRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SetCurrencyResponse:
    """Set the authenticated user's account currency."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.account_currency = body.currency
    # Default display_currency to account_currency on first setup.
    if user.display_currency is None:
        user.display_currency = body.currency
    # Auto-set language to the currency's default locale on first setup.
    if user.account_language is None:
        user.account_language = CURRENCY_DEFAULT_LANG.get(body.currency, "en_US")
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} set account_currency to {body.currency}")
    return SetCurrencyResponse(account_currency=user.account_currency)


@router.patch("/display", response_model=SetDisplayCurrencyResponse)
async def set_display_currency(
    body: SetDisplayCurrencyRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SetDisplayCurrencyResponse:
    """Set the user's active display currency (what they type and see in)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.display_currency = body.currency
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} set display_currency to {body.currency}")
    return SetDisplayCurrencyResponse(display_currency=user.display_currency)


@router.get("/rate", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    target: str = "KRW",
    base: str = "USD",
) -> ExchangeRateResponse:
    """Fetch the current exchange rate between two currencies.

    Proxied through the backend to avoid CORS and to cache results
    (1-hour TTL) so we don't hammer the upstream API.
    """
    base = base.upper()
    target = target.upper()

    if base not in ALLOWED_CURRENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Base must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}",
        )

    if target not in ALLOWED_CURRENCIES or target == base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target must be a different currency in: {', '.join(sorted(ALLOWED_CURRENCIES - {base}))}",
        )

    try:
        rate = await get_rate(base, target)
    except Exception:
        logger.exception("Failed to fetch exchange rate")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exchange rate service unavailable",
        )

    return ExchangeRateResponse(base=base, target=target, rate=rate)


# -- Account currency change -----------------------------------------------

class ChangeAccountCurrencyRequest(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        upper = value.upper()
        if upper not in ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {', '.join(sorted(ALLOWED_CURRENCIES))}")
        return upper


class ChangeAccountCurrencyResponse(BaseModel):
    account_currency: str
    rate_used: float
    commitments_converted: int
    snapshots_converted: int


@router.post("/change-account", response_model=ChangeAccountCurrencyResponse)
async def change_account_currency(
    body: ChangeAccountCurrencyRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChangeAccountCurrencyResponse:
    """Change the user's account currency, converting all stored amounts.

    This is a destructive operation — all commitment amounts and balance
    snapshots are multiplied by the current exchange rate. Historic accuracy
    is not guaranteed. The operation cannot be undone.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_currency = user.account_currency or "USD"
    new_currency = body.currency

    if old_currency == new_currency:
        return ChangeAccountCurrencyResponse(
            account_currency=new_currency,
            rate_used=1.0,
            commitments_converted=0,
            snapshots_converted=0,
        )

    # Fetch exchange rate before modifying anything.
    try:
        rate = await get_rate(old_currency, new_currency)
    except Exception:
        logger.exception("Failed to fetch exchange rate for currency change")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exchange rate service unavailable. Please try again later.",
        )

    rate_decimal = Decimal(str(rate))

    # Determine target decimal precision.
    # KRW and JPY use zero decimal places.
    zero_decimal = {"KRW", "JPY"}
    quantize_to = Decimal("1") if new_currency in zero_decimal else Decimal("0.01")

    # Convert all commitments.
    commit_result = await db.execute(
        select(Commitment).where(Commitment.user_id == user_id)
    )
    commitments = commit_result.scalars().all()
    for commitment in commitments:
        commitment.amount = (commitment.amount * rate_decimal).quantize(quantize_to)
    commitments_count = len(commitments)

    # Convert all balance snapshots.
    snap_result = await db.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.user_id == user_id)
    )
    snapshots = snap_result.scalars().all()
    for snapshot in snapshots:
        snapshot.balance = (snapshot.balance * rate_decimal).quantize(quantize_to)
    snapshots_count = len(snapshots)

    # Update user currency fields.
    user.account_currency = new_currency
    user.display_currency = new_currency
    # Auto-update language to the new currency's default.
    user.account_language = CURRENCY_DEFAULT_LANG.get(new_currency, user.account_language or "en_US")

    await db.commit()

    logger.info(
        "User %s changed account currency %s -> %s (rate=%.6f, %d commitments, %d snapshots)",
        user_id, old_currency, new_currency, rate, commitments_count, snapshots_count,
    )

    return ChangeAccountCurrencyResponse(
        account_currency=new_currency,
        rate_used=rate,
        commitments_converted=commitments_count,
        snapshots_converted=snapshots_count,
    )
