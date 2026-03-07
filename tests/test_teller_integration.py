"""Integration tests for the Teller enrollment flow and webhook processing.

Tests exercise the router endpoints directly with mocked Teller API calls
and an in-memory AsyncSession, following the project's AsyncMock pattern.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.teller_constants import TellerStatus
from app.models.teller_schemas import (
    TellerAccount,
    TellerEnrollRequest,
    TellerInstitution,
    TellerSelectAccountRequest,
)
from app.routers.teller import (
    _handle_enrollment_disconnected,
    _handle_transactions_processed,
    _initial_sync,
    _SyncContext,
    disconnect,
    enroll,
    get_status,
    select_account,
    webhook,
)
from app.services.teller_service import TellerApiError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_ENCRYPTION_KEY = "HXHxpM6dKwWEEeGQjH6fE37n5TREJGHbXSs84Vwn-Ys="
WEBHOOK_SECRET = "whsec_test_secret"


def _fake_settings(**overrides: object) -> MagicMock:
    """Build a mock Settings with Teller-relevant fields."""
    settings = MagicMock()
    settings.teller_encryption_key = overrides.get("encryption_key", FAKE_ENCRYPTION_KEY)
    settings.teller_webhook_secret = overrides.get("webhook_secret", WEBHOOK_SECRET)
    return settings


def _fake_enrollment(
    id: int = 1,
    user_id: int = 42,
    enrollment_id: str = "enr_abc123",
    institution_name: str = "Test Bank",
    status: str = TellerStatus.ACTIVE,
    account_id: str | None = "acc_001",
    account_name: str | None = "Checking",
    account_currency: str = "USD",
    access_token_encrypted: str = "",
    last_synced_at: datetime | None = None,
) -> MagicMock:
    """Build a mock TellerEnrollment row."""
    enrollment = MagicMock()
    enrollment.id = id
    enrollment.user_id = user_id
    enrollment.enrollment_id = enrollment_id
    enrollment.institution_name = institution_name
    enrollment.status = status
    enrollment.account_id = account_id
    enrollment.account_name = account_name
    enrollment.account_currency = account_currency
    enrollment.access_token_encrypted = access_token_encrypted
    enrollment.last_synced_at = last_synced_at
    return enrollment


def _fake_teller_account(
    id: str = "acc_001",
    name: str = "Everyday Checking",
    currency: str = "USD",
) -> TellerAccount:
    return TellerAccount(
        id=id,
        name=name,
        type="depository",
        subtype="checking",
        currency=currency,
        institution=TellerInstitution(id="inst_001", name="Test Bank"),
    )


def _sign_webhook(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest for webhook payloads."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# GET /teller/status
# ---------------------------------------------------------------------------


class TestGetStatus:
    """GET /status returns the user's enrollment state."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_no_enrollment_returns_disconnected(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        mock_repo.get_active_enrollment = AsyncMock(return_value=None)

        result = await get_status(user_id=1, db=mock_db)

        assert result.is_connected is False
        assert result.status == TellerStatus.DISCONNECTED

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_active_enrollment_returns_connected(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        enrollment = _fake_enrollment(status=TellerStatus.ACTIVE)
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)

        result = await get_status(user_id=42, db=mock_db)

        assert result.is_connected is True
        assert result.status == TellerStatus.ACTIVE
        assert result.institution_name == "Test Bank"
        assert result.account_name == "Checking"

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_syncing_enrollment_is_connected(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        enrollment = _fake_enrollment(status=TellerStatus.SYNCING)
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)

        result = await get_status(user_id=42, db=mock_db)

        assert result.is_connected is True
        assert result.status == TellerStatus.SYNCING


# ---------------------------------------------------------------------------
# POST /teller/enroll
# ---------------------------------------------------------------------------


class TestEnroll:
    """POST /enroll stores enrollment and returns accounts."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.encrypt_token", return_value="encrypted_token")
    @patch("app.routers.teller.teller_repository")
    async def test_enroll_returns_accounts(
        self,
        mock_repo: MagicMock,
        mock_encrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        new_enrollment = _fake_enrollment(
            status=TellerStatus.AWAITING_ACCOUNT,
            account_id=None,
        )
        mock_repo.get_active_enrollment = AsyncMock(return_value=None)
        mock_repo.create_enrollment = AsyncMock(return_value=new_enrollment)

        accounts = [_fake_teller_account()]
        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = accounts

        body = TellerEnrollRequest(
            access_token="test_token",
            enrollment_id="enr_new",
            institution="Test Bank",
        )
        settings = _fake_settings()

        result = await enroll(
            body=body,
            user_id=42,
            db=mock_db,
            request=mock_request,
            settings=settings,
        )

        assert result.status == TellerStatus.AWAITING_ACCOUNT
        assert len(result.accounts) == 1
        assert result.accounts[0].id == "acc_001"
        mock_repo.create_enrollment.assert_awaited_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.encrypt_token", return_value="encrypted_token")
    @patch("app.routers.teller.teller_repository")
    async def test_enroll_disconnects_existing(
        self,
        mock_repo: MagicMock,
        mock_encrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        existing = _fake_enrollment(id=99)
        new_enrollment = _fake_enrollment(id=100, status=TellerStatus.AWAITING_ACCOUNT)
        mock_repo.get_active_enrollment = AsyncMock(return_value=existing)
        mock_repo.create_enrollment = AsyncMock(return_value=new_enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = [_fake_teller_account()]

        body = TellerEnrollRequest(
            access_token="test_token",
            enrollment_id="enr_new2",
            institution="Test Bank",
        )

        await enroll(
            body=body, user_id=42, db=mock_db,
            request=mock_request, settings=_fake_settings(),
        )

        mock_repo.mark_disconnected.assert_awaited_once_with(mock_db, 99)

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.encrypt_token", return_value="encrypted_token")
    @patch("app.routers.teller.teller_repository")
    async def test_enroll_no_accounts_returns_502(
        self,
        mock_repo: MagicMock,
        mock_encrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        new_enrollment = _fake_enrollment(status=TellerStatus.AWAITING_ACCOUNT)
        mock_repo.get_active_enrollment = AsyncMock(return_value=None)
        mock_repo.create_enrollment = AsyncMock(return_value=new_enrollment)
        mock_repo.update_status = AsyncMock()

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = []

        body = TellerEnrollRequest(
            access_token="test_token",
            enrollment_id="enr_empty",
            institution="Test Bank",
        )

        with pytest.raises(HTTPException) as exc_info:
            await enroll(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# POST /teller/select-account
# ---------------------------------------------------------------------------


class TestSelectAccount:
    """POST /select-account validates the choice and kicks off sync."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_select_account_starts_sync(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"
        mock_request.app.state.teller_sync_tasks = {}
        mock_request.app.state.db_session_factory = MagicMock()

        enrollment = _fake_enrollment(
            status=TellerStatus.AWAITING_ACCOUNT,
            access_token_encrypted="enc_tok",
        )
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)
        mock_repo.transition_status = AsyncMock(return_value=True)
        mock_repo.update_account_details = AsyncMock()

        account = _fake_teller_account(id="acc_001", name="Everyday Checking")
        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = [account]

        body = TellerSelectAccountRequest(account_id="acc_001")

        with patch("app.routers.teller.asyncio") as mock_asyncio:
            mock_task = MagicMock()
            mock_asyncio.create_task.return_value = mock_task

            result = await select_account(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert result.status == TellerStatus.SYNCING
        assert result.account_name == "Everyday Checking"
        assert result.is_connected is True
        mock_repo.transition_status.assert_awaited_once_with(
            mock_db, enrollment.id,
            TellerStatus.AWAITING_ACCOUNT, TellerStatus.SYNCING,
        )

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_select_account_no_enrollment_returns_409(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_repo.get_active_enrollment = AsyncMock(return_value=None)

        body = TellerSelectAccountRequest(account_id="acc_001")

        with pytest.raises(HTTPException) as exc_info:
            await select_account(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_select_account_wrong_status_returns_409(self, mock_repo: MagicMock):
        """Enrollment exists but is ACTIVE (not AWAITING_ACCOUNT) → 409."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        enrollment = _fake_enrollment(status=TellerStatus.ACTIVE)
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)

        body = TellerSelectAccountRequest(account_id="acc_001")

        with pytest.raises(HTTPException) as exc_info:
            await select_account(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_select_unknown_account_returns_404(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        enrollment = _fake_enrollment(status=TellerStatus.AWAITING_ACCOUNT)
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = [
            _fake_teller_account(id="acc_other"),
        ]

        body = TellerSelectAccountRequest(account_id="acc_nonexistent")

        with pytest.raises(HTTPException) as exc_info:
            await select_account(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.routers.teller.fetch_accounts")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_concurrent_select_returns_409(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_fetch_accounts: MagicMock,
    ):
        """CAS failure means another request already transitioned the status."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        enrollment = _fake_enrollment(status=TellerStatus.AWAITING_ACCOUNT)
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)
        mock_repo.transition_status = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fetch_accounts.return_value = [_fake_teller_account()]

        body = TellerSelectAccountRequest(account_id="acc_001")

        with pytest.raises(HTTPException) as exc_info:
            await select_account(
                body=body, user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /teller/disconnect
# ---------------------------------------------------------------------------


class TestDisconnect:
    """DELETE /disconnect revokes access and marks enrollment disconnected."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.delete_enrollment")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_disconnect_revokes_and_marks(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_delete_enrollment: MagicMock,
    ):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"
        mock_request.app.state.teller_sync_tasks = {}

        enrollment = _fake_enrollment(account_id="acc_001")
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await disconnect(
            user_id=42, db=mock_db,
            request=mock_request, settings=_fake_settings(),
        )

        mock_delete_enrollment.assert_awaited_once_with(mock_client, "acc_001")
        mock_repo.mark_disconnected.assert_awaited_once_with(mock_db, enrollment.id)
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_disconnect_no_enrollment_returns_404(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_repo.get_active_enrollment = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await disconnect(
                user_id=42, db=mock_db,
                request=mock_request, settings=_fake_settings(),
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.routers.teller.delete_enrollment", side_effect=TellerApiError(500, "fail"))
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_disconnect_marks_even_if_api_fails(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_delete_enrollment: MagicMock,
    ):
        """Best-effort revocation: enrollment is marked disconnected even if
        the Teller API call fails."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"
        mock_request.app.state.teller_sync_tasks = {}

        enrollment = _fake_enrollment(account_id="acc_001")
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await disconnect(
            user_id=42, db=mock_db,
            request=mock_request, settings=_fake_settings(),
        )

        mock_repo.mark_disconnected.assert_awaited_once_with(mock_db, enrollment.id)

    @pytest.mark.asyncio
    @patch("app.routers.teller.delete_enrollment")
    @patch("app.routers.teller.build_teller_client")
    @patch("app.routers.teller.decrypt_token", return_value="plain_token")
    @patch("app.routers.teller.teller_repository")
    async def test_disconnect_cancels_inflight_sync(
        self,
        mock_repo: MagicMock,
        mock_decrypt: MagicMock,
        mock_build_client: MagicMock,
        mock_delete_enrollment: MagicMock,
    ):
        """An in-flight background sync task should be cancelled on disconnect."""
        mock_db = AsyncMock()
        mock_request = MagicMock()
        mock_request.app.state.teller_cert_path = "/tmp/cert.pem"
        mock_request.app.state.teller_key_path = "/tmp/key.pem"

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_request.app.state.teller_sync_tasks = {1: mock_task}

        enrollment = _fake_enrollment(id=1, account_id="acc_001")
        mock_repo.get_active_enrollment = AsyncMock(return_value=enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        await disconnect(
            user_id=42, db=mock_db,
            request=mock_request, settings=_fake_settings(),
        )

        mock_task.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# _initial_sync background task
# ---------------------------------------------------------------------------


def _make_sync_context(**overrides: object) -> _SyncContext:
    """Build a _SyncContext with sensible defaults for tests."""
    defaults: dict = {
        "factory": MagicMock(),
        "enrollment_id": 1,
        "teller_enrollment_id": "enr_abc123",
        "access_token": "tok_test",
        "cert_path": "/tmp/cert.pem",
        "key_path": "/tmp/key.pem",
        "user_id": 42,
        "account_id": "acc_001",
        "account_name": "Checking",
        "account_currency": "USD",
    }
    defaults.update(overrides)
    return _SyncContext(**defaults)


class TestInitialSync:
    """_initial_sync fetches balance + transactions then activates the enrollment."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    @patch("app.routers.teller.transaction_repository")
    @patch("app.routers.teller.balance_repository")
    @patch("app.routers.teller.convert_amount", new_callable=AsyncMock, return_value=Decimal("100.00"))
    @patch("app.routers.teller.get_user_account_currency", new_callable=AsyncMock, return_value="USD")
    @patch("app.routers.teller.fetch_transactions")
    @patch("app.routers.teller.fetch_balances")
    @patch("app.routers.teller.build_teller_client")
    async def test_happy_path_activates_enrollment(
        self,
        mock_build_client: MagicMock,
        mock_fetch_balances: MagicMock,
        mock_fetch_transactions: MagicMock,
        mock_get_currency: AsyncMock,
        mock_convert: AsyncMock,
        mock_balance_repo: MagicMock,
        mock_txn_repo: MagicMock,
        mock_teller_repo: MagicMock,
    ):
        # Teller API returns balance + one transaction.
        mock_client = AsyncMock()
        mock_build_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_fetch_balances.return_value = MagicMock(available="100.00")
        mock_fetch_transactions.return_value = [
            MagicMock(id="txn_001", amount="-50.00", date="2026-03-01",
                      description="Coffee", category="food_and_drink"),
        ]

        # Factory returns an async context manager yielding a mock session.
        mock_session = AsyncMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_teller_repo.transition_status = AsyncMock(return_value=True)
        mock_teller_repo.update_last_synced = AsyncMock()
        mock_balance_repo.create_from_teller = AsyncMock()
        mock_txn_repo.create_from_teller = AsyncMock()

        ctx = _make_sync_context(factory=factory)
        await _initial_sync(ctx)

        # Balance was written.
        mock_balance_repo.create_from_teller.assert_awaited_once()
        # Transaction was written.
        mock_txn_repo.create_from_teller.assert_awaited_once()
        # Status transitioned SYNCING → ACTIVE.
        mock_teller_repo.transition_status.assert_awaited_with(
            mock_session, 1, TellerStatus.SYNCING, TellerStatus.ACTIVE,
        )
        mock_teller_repo.update_last_synced.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    @patch("app.routers.teller.build_teller_client")
    async def test_teller_401_transitions_to_disconnected(
        self,
        mock_build_client: MagicMock,
        mock_teller_repo: MagicMock,
    ):
        """TellerApiError with 401 marks enrollment as DISCONNECTED."""
        mock_build_client.return_value.__aenter__ = AsyncMock(
            side_effect=TellerApiError(401, "Token revoked"),
        )
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_teller_repo.transition_status = AsyncMock(return_value=True)

        ctx = _make_sync_context(factory=factory)
        await _initial_sync(ctx)

        mock_teller_repo.transition_status.assert_awaited_once_with(
            mock_session, 1, TellerStatus.SYNCING, TellerStatus.DISCONNECTED,
        )

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    @patch("app.routers.teller.build_teller_client")
    async def test_teller_500_transitions_to_error(
        self,
        mock_build_client: MagicMock,
        mock_teller_repo: MagicMock,
    ):
        """TellerApiError with non-auth status code marks enrollment as ERROR."""
        mock_build_client.return_value.__aenter__ = AsyncMock(
            side_effect=TellerApiError(500, "Internal server error"),
        )
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_teller_repo.transition_status = AsyncMock(return_value=True)

        ctx = _make_sync_context(factory=factory)
        await _initial_sync(ctx)

        mock_teller_repo.transition_status.assert_awaited_once_with(
            mock_session, 1, TellerStatus.SYNCING, TellerStatus.ERROR,
        )

    @pytest.mark.asyncio
    @patch("app.routers.teller.build_teller_client")
    async def test_cancelled_error_re_raises(
        self,
        mock_build_client: MagicMock,
    ):
        """CancelledError propagates so asyncio can clean up the task."""
        mock_build_client.return_value.__aenter__ = AsyncMock(
            side_effect=asyncio.CancelledError(),
        )
        mock_build_client.return_value.__aexit__ = AsyncMock(return_value=False)

        ctx = _make_sync_context()

        with pytest.raises(asyncio.CancelledError):
            await _initial_sync(ctx)


# ---------------------------------------------------------------------------
# POST /teller/webhook — enrollment.disconnected
# ---------------------------------------------------------------------------


class TestWebhookEnrollmentDisconnected:
    """Webhook: enrollment.disconnected marks the enrollment as disconnected."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_marks_enrollment_disconnected(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        enrollment = _fake_enrollment(enrollment_id="enr_abc123")
        mock_repo.get_enrollment_by_enrollment_id = AsyncMock(return_value=enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        payload = {
            "type": "enrollment.disconnected",
            "payload": {"enrollment_id": "enr_abc123"},
        }

        await _handle_enrollment_disconnected(mock_db, payload)

        mock_repo.mark_disconnected.assert_awaited_once_with(mock_db, enrollment.id)

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_ignores_unknown_enrollment(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        mock_repo.get_enrollment_by_enrollment_id = AsyncMock(return_value=None)

        payload = {
            "type": "enrollment.disconnected",
            "payload": {"enrollment_id": "enr_unknown"},
        }

        # Should not raise — just logs and moves on.
        await _handle_enrollment_disconnected(mock_db, payload)

        mock_repo.mark_disconnected.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_missing_enrollment_id_in_payload(self, mock_repo: MagicMock):
        mock_db = AsyncMock()
        payload = {
            "type": "enrollment.disconnected",
            "payload": {},
        }

        await _handle_enrollment_disconnected(mock_db, payload)

        mock_repo.get_enrollment_by_enrollment_id.assert_not_called()


# ---------------------------------------------------------------------------
# POST /teller/webhook — transactions.processed
# ---------------------------------------------------------------------------


class TestWebhookTransactionsProcessed:
    """Webhook: transactions.processed ingests new transactions."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.convert_amount", new_callable=AsyncMock, return_value=Decimal("25.50"))
    @patch("app.routers.teller.get_user_account_currency", new_callable=AsyncMock, return_value="USD")
    @patch("app.routers.teller.transaction_repository")
    @patch("app.routers.teller.teller_repository")
    async def test_ingests_transactions(
        self,
        mock_teller_repo: MagicMock,
        mock_txn_repo: MagicMock,
        mock_get_currency: AsyncMock,
        mock_convert: AsyncMock,
    ):
        mock_db = AsyncMock()
        enrollment = _fake_enrollment()
        mock_teller_repo.get_enrollment_by_account = AsyncMock(return_value=enrollment)
        mock_txn_repo.create_from_teller = AsyncMock()

        settings = _fake_settings()
        payload = {
            "type": "transactions.processed",
            "payload": {
                "account_id": "acc_001",
                "transactions": [
                    {
                        "id": "txn_001",
                        "amount": "-25.50",
                        "date": "2026-03-01",
                        "description": "Coffee Shop",
                        "category": "food_and_drink",
                    },
                ],
            },
        }

        await _handle_transactions_processed(mock_db, payload, settings)

        # Verify currency conversion was called with parsed amount.
        mock_convert.assert_awaited_once_with(Decimal("25.50"), "USD", "USD")

        mock_txn_repo.create_from_teller.assert_awaited_once()
        call_kwargs = mock_txn_repo.create_from_teller.call_args.kwargs
        assert call_kwargs["user_id"] == 42
        assert call_kwargs["teller_transaction_id"] == "txn_001"
        assert call_kwargs["merchant"] == "Coffee Shop"
        assert call_kwargs["category"] == "food_and_drink"
        assert call_kwargs["amount"] == Decimal("25.50")
        assert call_kwargs["purchase_date"] == datetime(2026, 3, 1, tzinfo=UTC)

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_unknown_account_ignored(self, mock_teller_repo: MagicMock):
        mock_db = AsyncMock()
        mock_teller_repo.get_enrollment_by_account = AsyncMock(return_value=None)

        settings = _fake_settings()
        payload = {
            "type": "transactions.processed",
            "payload": {"account_id": "acc_unknown", "transactions": []},
        }

        # Should not raise.
        await _handle_transactions_processed(mock_db, payload, settings)

    @pytest.mark.asyncio
    @patch("app.routers.teller.convert_amount", new_callable=AsyncMock, return_value=Decimal("0"))
    @patch("app.routers.teller.get_user_account_currency", new_callable=AsyncMock, return_value="USD")
    @patch("app.routers.teller.transaction_repository")
    @patch("app.routers.teller.teller_repository")
    async def test_invalid_amount_skipped(
        self,
        mock_teller_repo: MagicMock,
        mock_txn_repo: MagicMock,
        mock_get_currency: AsyncMock,
        mock_convert: AsyncMock,
    ):
        mock_db = AsyncMock()
        enrollment = _fake_enrollment()
        mock_teller_repo.get_enrollment_by_account = AsyncMock(return_value=enrollment)

        settings = _fake_settings()
        payload = {
            "type": "transactions.processed",
            "payload": {
                "account_id": "acc_001",
                "transactions": [
                    {"id": "txn_bad", "amount": "not_a_number", "date": "2026-03-01",
                     "description": "Bad", "category": None},
                ],
            },
        }

        await _handle_transactions_processed(mock_db, payload, settings)

        mock_txn_repo.create_from_teller.assert_not_called()


# ---------------------------------------------------------------------------
# POST /teller/webhook — signature validation (full endpoint)
# ---------------------------------------------------------------------------


class TestWebhookSignature:
    """The webhook endpoint rejects requests with invalid signatures."""

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_401(self):
        payload_bytes = json.dumps({"type": "test"}).encode()

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {"x-teller-signature": "bad_sig"}
        mock_request.json = AsyncMock(return_value={"type": "test"})

        with pytest.raises(HTTPException) as exc_info:
            await webhook(request=mock_request, settings=_fake_settings())

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self):
        payload = {"type": "unknown.event"}
        payload_bytes = json.dumps(payload).encode()
        signature = _sign_webhook(payload_bytes)

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {"x-teller-signature": signature}
        mock_request.json = AsyncMock(return_value=payload)
        mock_request.app.state.db_session_factory = MagicMock()

        mock_session = AsyncMock()
        mock_request.app.state.db_session_factory.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_request.app.state.db_session_factory.return_value.__aexit__ = AsyncMock(
            return_value=False
        )

        result = await webhook(request=mock_request, settings=_fake_settings())

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_malformed_json_returns_ok(self):
        """Webhook returns 200 even with malformed JSON to prevent retry storms."""
        payload_bytes = b"not json at all"
        signature = _sign_webhook(payload_bytes)

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {"x-teller-signature": signature}
        mock_request.json = AsyncMock(side_effect=ValueError("bad json"))
        mock_request.app.state.db_session_factory = MagicMock()

        result = await webhook(request=mock_request, settings=_fake_settings())

        assert result == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /teller/webhook — end-to-end dispatch
# ---------------------------------------------------------------------------


class TestWebhookDispatch:
    """Signed webhook payloads are dispatched to the correct handler."""

    @pytest.mark.asyncio
    @patch("app.routers.teller.teller_repository")
    async def test_enrollment_disconnected_dispatches(self, mock_repo: MagicMock):
        """A signed enrollment.disconnected event marks the enrollment via full webhook()."""
        enrollment = _fake_enrollment(enrollment_id="enr_dispatch")
        mock_repo.get_enrollment_by_enrollment_id = AsyncMock(return_value=enrollment)
        mock_repo.mark_disconnected = AsyncMock()

        payload = {
            "type": "enrollment.disconnected",
            "payload": {"enrollment_id": "enr_dispatch"},
        }
        payload_bytes = json.dumps(payload).encode()
        signature = _sign_webhook(payload_bytes)

        mock_session = AsyncMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=payload_bytes)
        mock_request.headers = {"x-teller-signature": signature}
        mock_request.json = AsyncMock(return_value=payload)
        mock_request.app.state.db_session_factory = factory

        result = await webhook(request=mock_request, settings=_fake_settings())

        assert result == {"status": "ok"}
        mock_repo.mark_disconnected.assert_awaited_once_with(mock_session, enrollment.id)
