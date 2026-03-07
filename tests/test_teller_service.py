"""Tests for Teller service: webhook signature verification and API error mapping.

Covers HMAC-SHA256 verification, timing-safe comparison, and the
TellerApiError exception contract.
"""
from __future__ import annotations

import hashlib
import hmac

import pytest

from app.services.teller_service import TellerApiError, verify_webhook_signature


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


class TestVerifyWebhookSignature:
    """verify_webhook_signature should validate HMAC-SHA256 correctly."""

    SECRET = "whsec_test_secret_abc123"

    def _sign(self, payload: bytes, secret: str | None = None) -> str:
        """Compute the expected HMAC-SHA256 hex digest."""
        key = (secret or self.SECRET).encode()
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def test_valid_signature_matches(self):
        payload = b'{"type":"enrollment.disconnected","payload":{}}'
        signature = self._sign(payload)

        assert verify_webhook_signature(payload, signature, self.SECRET) is True

    def test_wrong_signature_rejected(self):
        payload = b'{"type":"enrollment.disconnected","payload":{}}'

        assert verify_webhook_signature(payload, "badhex", self.SECRET) is False

    def test_wrong_secret_rejected(self):
        payload = b'{"type":"enrollment.disconnected","payload":{}}'
        signature = self._sign(payload, secret="wrong_secret")

        assert verify_webhook_signature(payload, signature, self.SECRET) is False

    def test_tampered_payload_rejected(self):
        original = b'{"amount":"100.00"}'
        signature = self._sign(original)
        tampered = b'{"amount":"999.99"}'

        assert verify_webhook_signature(tampered, signature, self.SECRET) is False

    def test_empty_payload(self):
        payload = b""
        signature = self._sign(payload)

        assert verify_webhook_signature(payload, signature, self.SECRET) is True

    def test_empty_signature_rejected(self):
        payload = b'{"type":"test"}'

        assert verify_webhook_signature(payload, "", self.SECRET) is False

    def test_binary_payload(self):
        payload = b"\x00\x01\x02\xff\xfe"
        signature = self._sign(payload)

        assert verify_webhook_signature(payload, signature, self.SECRET) is True


# ---------------------------------------------------------------------------
# TellerApiError contract
# ---------------------------------------------------------------------------


class TestTellerApiError:
    """TellerApiError should expose status_code and detail as read-only properties."""

    def test_properties_match_constructor(self):
        err = TellerApiError(401, "Access token revoked")

        assert err.status_code == 401
        assert err.detail == "Access token revoked"
