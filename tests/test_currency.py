"""Tests for currency endpoints and validation.

Covers the Pydantic model validation, the set-currency endpoint logic,
and the exchange rate cache behavior.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.routers.currency import (
    ALLOWED_CURRENCIES,
    ExchangeRateResponse,
    SetCurrencyRequest,
    get_exchange_rate,
    set_account_currency,
)
from app.services.currency_service import (
    _CACHE_TTL_SECONDS,
    _rate_cache,
)


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------


class TestSetCurrencyRequestValidation:
    """The request model should accept only USD and KRW, case-insensitive."""

    def test_usd_uppercase(self):
        req = SetCurrencyRequest(currency="USD")
        assert req.currency == "USD"

    def test_krw_lowercase(self):
        req = SetCurrencyRequest(currency="krw")
        assert req.currency == "KRW"

    def test_mixed_case(self):
        req = SetCurrencyRequest(currency="Usd")
        assert req.currency == "USD"

    def test_invalid_currency_rejected(self):
        with pytest.raises(ValueError):
            SetCurrencyRequest(currency="EUR")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            SetCurrencyRequest(currency="")

    def test_allowed_currencies_complete(self):
        assert ALLOWED_CURRENCIES == {"USD", "KRW"}


# ---------------------------------------------------------------------------
# set_account_currency endpoint
# ---------------------------------------------------------------------------


class TestSetAccountCurrency:
    """The PATCH /currency/account endpoint should persist the currency choice."""

    @pytest.mark.asyncio
    async def test_sets_currency_on_user(self):
        mock_user = MagicMock()
        mock_user.account_currency = None
        mock_user.display_currency = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        body = SetCurrencyRequest(currency="KRW")
        response = await set_account_currency(body=body, user_id=1, db=mock_db)

        assert mock_user.account_currency == "KRW"
        # display_currency defaults to account_currency on first setup.
        assert mock_user.display_currency == "KRW"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_user)
        assert response.account_currency == "KRW"

    @pytest.mark.asyncio
    async def test_user_not_found_returns_404(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        body = SetCurrencyRequest(currency="USD")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await set_account_currency(body=body, user_id=999, db=mock_db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Exchange rate endpoint + cache
# ---------------------------------------------------------------------------


class TestGetExchangeRate:
    """The GET /currency/rate endpoint should proxy upstream and cache results."""

    def setup_method(self):
        _rate_cache.clear()

    @pytest.mark.asyncio
    async def test_rejects_usd_target(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_exchange_rate(target="USD")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_unsupported_currency(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_exchange_rate(target="EUR")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_fetches_from_upstream(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"KRW": 1345.50}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.currency_service.httpx.AsyncClient", return_value=mock_client):
            result = await get_exchange_rate(target="KRW")

        assert result.base == "USD"
        assert result.target == "KRW"
        assert result.rate == 1345.50

    @pytest.mark.asyncio
    async def test_returns_cached_rate(self):
        """A fresh cached rate should be returned without hitting upstream."""
        _rate_cache["USD:KRW"] = (time.time(), 1300.0)

        # If this tried to hit the network, it would fail since we don't mock httpx.
        result = await get_exchange_rate(target="KRW")

        assert result.rate == 1300.0
        assert result.target == "KRW"

    @pytest.mark.asyncio
    async def test_stale_cache_refetches(self):
        """An expired cached rate should trigger a fresh upstream fetch."""
        stale_time = time.time() - _CACHE_TTL_SECONDS - 10
        _rate_cache["USD:KRW"] = (stale_time, 1200.0)

        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {"KRW": 1350.0}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.currency_service.httpx.AsyncClient", return_value=mock_client):
            result = await get_exchange_rate(target="KRW")

        assert result.rate == 1350.0
        # Cache should be updated.
        assert _rate_cache["USD:KRW"][1] == 1350.0

    @pytest.mark.asyncio
    async def test_upstream_failure_returns_502(self):
        """Network errors should produce a 502 response."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        from fastapi import HTTPException

        with patch("app.services.currency_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_exchange_rate(target="KRW")

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_missing_rate_in_response_returns_502(self):
        """If upstream returns no rate for the target, return 502."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"rates": {}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        from fastapi import HTTPException

        with patch("app.services.currency_service.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_exchange_rate(target="KRW")

        assert exc_info.value.status_code == 502
