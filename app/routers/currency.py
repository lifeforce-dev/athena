"""Currency-related endpoints: set account currency, fetch exchange rates."""
from __future__ import annotations

import logging
import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.orm import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/currency", tags=["currency"])

ALLOWED_CURRENCIES = {"USD", "KRW"}

EXCHANGE_RATE_URL = "https://api.exchangerate.host/latest"

# Simple in-memory cache: (timestamp, rate_dict).
_rate_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL_SECONDS = 3600


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
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} set account_currency to {body.currency}")
    return SetCurrencyResponse(account_currency=user.account_currency)


@router.get("/rate", response_model=ExchangeRateResponse)
async def get_exchange_rate(
    target: str = "KRW",
) -> ExchangeRateResponse:
    """Fetch the current USD exchange rate for a target currency.

    Proxied through the backend to avoid CORS and to cache results
    (1-hour TTL) so we don't hammer the upstream API.
    """
    target = target.upper()

    if target not in ALLOWED_CURRENCIES or target == "USD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target must be a non-USD currency in: {', '.join(sorted(ALLOWED_CURRENCIES - {'USD'}))}",
        )

    now = time.time()

    # Return cached rate if fresh.
    if target in _rate_cache:
        cached_time, cached_rate = _rate_cache[target]
        if now - cached_time < _CACHE_TTL_SECONDS:
            return ExchangeRateResponse(base="USD", target=target, rate=cached_rate)

    # Fetch from upstream.
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(EXCHANGE_RATE_URL, params={"base": "USD", "symbols": target})
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Failed to fetch exchange rate from upstream")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exchange rate service unavailable",
        )

    rate = data.get("rates", {}).get(target)
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Exchange rate not found in upstream response",
        )

    _rate_cache[target] = (now, float(rate))
    return ExchangeRateResponse(base="USD", target=target, rate=float(rate))
