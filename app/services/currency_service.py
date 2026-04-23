"""Currency conversion service.

The backend is the single source of truth for currency conversion.
Monetary values are stored in the user's *account currency*. When the
user's active display_currency differs from their account_currency,
incoming amounts are converted here before reaching the DB.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import User

logger = logging.getLogger(__name__)

EXCHANGE_RATE_URL = "https://api.frankfurter.dev/v1/latest"

ALLOWED_CURRENCIES = {"USD", "KRW", "JPY", "EUR", "GBP", "CNY", "BRL"}


class CurrencyConversionError(Exception):
    """Raised when currency conversion fails."""

    _base: str
    _target: str
    _reason: str

    def __init__(self, base: str, target: str, reason: str) -> None:
        self._base = base
        self._target = target
        self._reason = reason
        super().__init__(f"Cannot convert {base} -> {target}: {reason}")

    @property
    def base(self) -> str:
        return self._base

    @property
    def target(self) -> str:
        return self._target

    @property
    def reason(self) -> str:
        return self._reason

# In-memory cache: "FROM:TO" -> (timestamp, rate).
_rate_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL_SECONDS = 3600


async def get_rate(base: str, target: str) -> float:
    """Fetch the exchange rate from *base* to *target* (1-hour cache)."""
    base = base.upper()
    target = target.upper()

    if base == target:
        return 1.0

    key = f"{base}:{target}"
    now = time.time()

    if key in _rate_cache:
        cached_time, cached_rate = _rate_cache[key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            return cached_rate

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(EXCHANGE_RATE_URL, params={"from": base, "to": target})
        resp.raise_for_status()
        data = resp.json()

    rate = data.get("rates", {}).get(target)
    if rate is None:
        raise CurrencyConversionError(base, target, "rate not found in API response")

    _rate_cache[key] = (now, float(rate))
    return float(rate)


async def get_rate_with_fallback(base: str, target: str) -> float:
    """Like get_rate(), but returns a stale cached rate if the API is unreachable.

    The daily balance sync refreshes rates regularly. If the API is down during a
    webhook or enrollment, a slightly stale rate (up to ~24h old) is acceptable
    because the daily balance sync will reconcile with a fresh rate anyway.
    """
    try:
        return await get_rate(base, target)
    except (httpx.HTTPError, CurrencyConversionError) as exc:
        key = f"{base.upper()}:{target.upper()}"
        if key in _rate_cache:
            logger.warning("Rate API down, using stale cached rate for %s", key)
            _, stale_rate = _rate_cache[key]
            return stale_rate
        raise CurrencyConversionError(
            base, target, f"API unreachable and no cached rate available ({exc})"
        ) from exc


class UserCurrencyInfo:
    """Lightweight carrier for a user's currency pair."""

    __slots__ = ("account", "display")

    def __init__(self, account: str, display: str) -> None:
        self.account = account
        self.display = display

    @property
    def needs_conversion(self) -> bool:
        return self.display != self.account


async def get_user_currencies(
    user_id: int,
    db: AsyncSession,
    display_override: str | None = None,
) -> UserCurrencyInfo:
    """Return the user's account and display currencies.

    When `display_override` is provided (from the X-Display-Currency header),
    it takes precedence over the DB value. This eliminates race conditions
    between the frontend toggle and the backend conversion.
    """
    result = await db.execute(
        select(User.account_currency, User.display_currency).where(User.id == user_id)
    )
    row = result.one_or_none()
    account = (row[0] if row and row[0] else "USD")

    if display_override and display_override.upper() in ALLOWED_CURRENCIES:
        display = display_override.upper()
    else:
        display = (row[1] if row and row[1] else account)

    return UserCurrencyInfo(account=account, display=display)


async def to_account_currency(amount: Decimal, info: UserCurrencyInfo) -> Decimal:
    """Convert an amount from display currency to account currency.

    Returns unchanged if both currencies match.
    """
    if not info.needs_conversion:
        return amount

    rate = await get_rate(info.display, info.account)
    return (amount * Decimal(str(rate))).quantize(Decimal("0.01"))


async def convert_amount(
    amount: Decimal,
    source_currency: str,
    target_currency: str,
) -> Decimal:
    """Convert an amount between any two currencies.

    When source and target are the same, get_rate_with_fallback returns 1.0
    and the multiplication is a no-op — no branching needed by callers.
    """
    rate = await get_rate_with_fallback(source_currency, target_currency)
    return (amount * Decimal(str(rate))).quantize(Decimal("0.01"))


async def get_user_account_currency(user_id: int, db: AsyncSession) -> str:
    """Return the user's account currency, defaulting to USD."""
    result = await db.execute(
        select(User.account_currency).where(User.id == user_id)
    )
    row = result.scalar_one_or_none()
    return row if row else "USD"
