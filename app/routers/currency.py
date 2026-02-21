"""Currency-related endpoints: set account currency, fetch exchange rates."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.orm import User
from app.services.currency_service import get_rate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])

ALLOWED_CURRENCIES = {"USD", "KRW", "JPY", "EUR", "GBP"}

# Maps currency code to default locale for auto-setting account_language.
CURRENCY_DEFAULT_LANG: dict[str, str] = {
    "USD": "en_US",
    "KRW": "ko_KR",
    "JPY": "ja_JP",
    "EUR": "en_US",
    "GBP": "en_US",
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
