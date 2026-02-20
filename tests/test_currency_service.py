"""Tests for the currency conversion service.

Validates that to_account_currency correctly converts between display
and account currencies, and that get_user_currencies reads the right
values from the User model.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.currency_service import (
    UserCurrencyInfo,
    get_user_currencies,
    to_account_currency,
)


# ---------------------------------------------------------------------------
# to_account_currency
# ---------------------------------------------------------------------------

class TestToAccountCurrency:
    """Unit tests for to_account_currency (no DB, mocked rate)."""

    @pytest.mark.asyncio
    async def test_same_currency_passthrough(self):
        """When display == account, amount passes through unchanged."""
        info = UserCurrencyInfo(account="KRW", display="KRW")
        result = await to_account_currency(Decimal("135000"), info)
        assert result == Decimal("135000")

    @pytest.mark.asyncio
    async def test_usd_display_to_krw_account(self):
        """USD $100 at rate 1350 = 135,000 KRW."""
        info = UserCurrencyInfo(account="KRW", display="USD")
        with patch("app.services.currency_service.get_rate", new_callable=AsyncMock, return_value=1350.0) as mock:
            result = await to_account_currency(Decimal("100"), info)
        assert result == Decimal("135000.00")
        mock.assert_awaited_once_with("USD", "KRW")

    @pytest.mark.asyncio
    async def test_krw_display_to_usd_account(self):
        """135,000 KRW at rate (KRW->USD) ~0.000741 = $100."""
        info = UserCurrencyInfo(account="USD", display="KRW")
        # Rate from KRW to USD is 1/1350 ~ 0.000740740...
        with patch("app.services.currency_service.get_rate", new_callable=AsyncMock, return_value=0.00074074074):
            result = await to_account_currency(Decimal("135000"), info)
        assert result == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_negative_amount_preserved(self):
        """Negative amounts (expenses) keep their sign after conversion."""
        info = UserCurrencyInfo(account="KRW", display="USD")
        with patch("app.services.currency_service.get_rate", new_callable=AsyncMock, return_value=1350.0):
            result = await to_account_currency(Decimal("-100"), info)
        assert result == Decimal("-135000.00")

    @pytest.mark.asyncio
    async def test_rounds_to_two_decimals(self):
        """Fractional results are rounded to 2 decimal places."""
        info = UserCurrencyInfo(account="USD", display="KRW")
        # 5000 KRW * (1/1350) = 3.7037...
        with patch("app.services.currency_service.get_rate", new_callable=AsyncMock, return_value=0.00074074074):
            result = await to_account_currency(Decimal("5000"), info)
        assert result == Decimal("3.70")

    @pytest.mark.asyncio
    async def test_zero_passthrough(self):
        """Zero is zero regardless of conversion."""
        info = UserCurrencyInfo(account="KRW", display="USD")
        with patch("app.services.currency_service.get_rate", new_callable=AsyncMock, return_value=1350.0):
            result = await to_account_currency(Decimal("0"), info)
        assert result == Decimal("0.00")


class TestUserCurrencyInfo:
    """Tests for the needs_conversion property."""

    def test_same_currency_no_conversion(self):
        info = UserCurrencyInfo(account="USD", display="USD")
        assert not info.needs_conversion

    def test_different_currency_needs_conversion(self):
        info = UserCurrencyInfo(account="KRW", display="USD")
        assert info.needs_conversion


# ---------------------------------------------------------------------------
# get_user_currencies
# ---------------------------------------------------------------------------

class TestGetUserCurrencies:
    """Tests that get_user_currencies reads both fields and uses defaults."""

    @pytest.mark.asyncio
    async def test_returns_both_currencies(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = ("KRW", "USD")
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await get_user_currencies(1, mock_db)
        assert info.account == "KRW"
        assert info.display == "USD"

    @pytest.mark.asyncio
    async def test_defaults_to_usd_when_null(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await get_user_currencies(1, mock_db)
        assert info.account == "USD"
        assert info.display == "USD"

    @pytest.mark.asyncio
    async def test_display_defaults_to_account_when_null(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = ("KRW", None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await get_user_currencies(1, mock_db)
        assert info.account == "KRW"
        assert info.display == "KRW"

    @pytest.mark.asyncio
    async def test_header_override_takes_precedence(self):
        """X-Display-Currency header overrides the DB value."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = ("USD", "USD")
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await get_user_currencies(1, mock_db, display_override="KRW")
        assert info.account == "USD"
        assert info.display == "KRW"
        assert info.needs_conversion

    @pytest.mark.asyncio
    async def test_header_override_ignores_invalid(self):
        """Invalid header values are ignored, falling back to DB."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = ("USD", "USD")
        mock_db.execute = AsyncMock(return_value=mock_result)

        info = await get_user_currencies(1, mock_db, display_override="EUR")
        assert info.display == "USD"
        assert not info.needs_conversion


# ---------------------------------------------------------------------------
# Intake conversion (router-level integration)
# ---------------------------------------------------------------------------

class TestIntakeConversion:
    """Verify routers convert display-currency amounts to account currency.

    Each test patches get_user_currencies and to_account_currency at the
    router import site, then calls the endpoint to confirm the converted
    amount reaches the service/repo layer.
    """

    @pytest.mark.asyncio
    async def test_create_commitment_converts_amount(self):
        """POST /commitments converts display amount to account currency."""
        from app.routers.commitments import create_commitment

        info = UserCurrencyInfo(account="KRW", display="USD")
        converted = Decimal("135000.00")

        now = datetime.now()
        row = SimpleNamespace(
            id=1, user_id=1, name="Rent", amount=converted,
            frequency="monthly", day_of_month=1, interval_days=None,
            anchor_date=None, one_time_date=None,
            start_date=date(2026, 1, 1), end_date=None,
            is_paycheck=False, is_active=True,
            created_at=now, updated_at=now,
        )

        with (
            patch("app.routers.commitments.get_user_currencies", new_callable=AsyncMock, return_value=info),
            patch("app.routers.commitments.to_account_currency", new_callable=AsyncMock, return_value=converted) as mock_convert,
            patch("app.routers.commitments.service.create_commitment", new_callable=AsyncMock, return_value=row),
        ):
            mock_db = AsyncMock()

            from app.models.commitment_schemas import CommitmentCreate
            data = CommitmentCreate(
                name="Rent",
                amount=Decimal("100.00"),
                frequency="monthly",
                day_of_month=1,
                start_date=date(2026, 1, 1),
            )
            await create_commitment(data=data, user_id=1, db=mock_db, x_display_currency=None)

            # The raw $100 display amount should have been converted.
            mock_convert.assert_awaited_once_with(Decimal("100.00"), info)
            # data.amount was mutated in-place before service call.
            assert data.amount == converted

    @pytest.mark.asyncio
    async def test_update_commitment_converts_amount(self):
        """PUT /commitments/{id} converts amount when present."""
        from app.routers.commitments import update_commitment

        info = UserCurrencyInfo(account="KRW", display="USD")
        converted = Decimal("67500.00")

        now = datetime.now()
        row = SimpleNamespace(
            id=1, user_id=1, name="Groceries", amount=converted,
            frequency="weekly", day_of_month=None, interval_days=None,
            anchor_date=date(2026, 1, 5), one_time_date=None,
            start_date=date(2026, 1, 1), end_date=None,
            is_paycheck=False, is_active=True,
            created_at=now, updated_at=now,
        )

        with (
            patch("app.routers.commitments.get_user_currencies", new_callable=AsyncMock, return_value=info),
            patch("app.routers.commitments.to_account_currency", new_callable=AsyncMock, return_value=converted) as mock_convert,
            patch("app.routers.commitments.service.update_commitment", new_callable=AsyncMock, return_value=row),
        ):
            mock_db = AsyncMock()

            from app.models.commitment_schemas import CommitmentUpdate
            data = CommitmentUpdate(amount=Decimal("50.00"))
            await update_commitment(commitment_id=1, data=data, user_id=1, db=mock_db, x_display_currency=None)

            mock_convert.assert_awaited_once_with(Decimal("50.00"), info)
            assert data.amount == converted

    @pytest.mark.asyncio
    async def test_update_commitment_skips_conversion_when_no_amount(self):
        """PUT /commitments/{id} does not convert if amount is absent."""
        from app.routers.commitments import update_commitment

        now = datetime.now()
        row = SimpleNamespace(
            id=1, user_id=1, name="Updated", amount=Decimal("100"),
            frequency="monthly", day_of_month=1, interval_days=None,
            anchor_date=None, one_time_date=None,
            start_date=date(2026, 1, 1), end_date=None,
            is_paycheck=False, is_active=True,
            created_at=now, updated_at=now,
        )

        with (
            patch("app.routers.commitments.get_user_currencies", new_callable=AsyncMock) as mock_get,
            patch("app.routers.commitments.to_account_currency", new_callable=AsyncMock) as mock_convert,
            patch("app.routers.commitments.service.update_commitment", new_callable=AsyncMock, return_value=row),
        ):
            mock_db = AsyncMock()

            from app.models.commitment_schemas import CommitmentUpdate
            data = CommitmentUpdate(name="Updated")
            await update_commitment(commitment_id=1, data=data, user_id=1, db=mock_db, x_display_currency=None)

            # No amount means no currency lookup or conversion.
            mock_get.assert_not_awaited()
            mock_convert.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_manual_balance_converts_amount(self):
        """POST /balance/manual converts display balance to account currency."""
        from app.routers.balance import create_manual_balance

        info = UserCurrencyInfo(account="KRW", display="USD")
        converted = Decimal("1350000.00")

        now = datetime.now()
        row = SimpleNamespace(
            id=1, user_id=1, balance=converted,
            observed_at=now, source="manual",
            account_label=None, created_at=now,
        )

        with (
            patch("app.routers.balance.get_user_currencies", new_callable=AsyncMock, return_value=info),
            patch("app.routers.balance.to_account_currency", new_callable=AsyncMock, return_value=converted) as mock_convert,
            patch("app.routers.balance.repo.create_manual", new_callable=AsyncMock, return_value=row),
        ):
            mock_db = AsyncMock()

            from app.models.balance_schemas import ManualBalanceCreate
            data = ManualBalanceCreate(balance=Decimal("1000.00"), observed_at=now)
            await create_manual_balance(data=data, user_id=1, db=mock_db, x_display_currency=None)

            mock_convert.assert_awaited_once_with(Decimal("1000.00"), info)
            assert data.balance == converted

    @pytest.mark.asyncio
    async def test_scenario_converts_override_amounts(self):
        """POST /projection/scenario converts amount_overrides."""
        from app.routers.projection import run_scenario

        info = UserCurrencyInfo(account="KRW", display="USD")

        async def fake_convert(amount: Decimal, _info: UserCurrencyInfo) -> Decimal:
            return (amount * Decimal("1350")).quantize(Decimal("0.01"))

        with (
            patch("app.routers.projection.get_user_currencies", new_callable=AsyncMock, return_value=info),
            patch("app.routers.projection.to_account_currency", side_effect=fake_convert) as mock_convert,
            patch("app.routers.projection.build_scenario_projection", new_callable=AsyncMock) as mock_build,
        ):
            mock_db = AsyncMock()
            mock_build.return_value = MagicMock()

            from app.models.schemas import ScenarioRequest
            from datetime import date
            data = ScenarioRequest(
                as_of=date(2026, 2, 19),
                amount_overrides={10: Decimal("100.00"), 20: Decimal("50.00")},
            )
            await run_scenario(body=data, user_id=1, db=mock_db, x_display_currency=None)
            assert mock_convert.await_count == 2
            # build_scenario_projection should receive KRW amounts.
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs["amount_overrides"][10] == Decimal("135000.00")
            assert call_kwargs["amount_overrides"][20] == Decimal("67500.00")
