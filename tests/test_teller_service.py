"""Tests for Teller service: webhook signature verification and API error mapping.

Covers HMAC-SHA256 verification, timing-safe comparison, the
TellerApiError exception contract, nonce generation, and Ed25519 token
signature verification.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.teller_service import (
    TellerApiError,
    generate_enrollment_nonce,
    verify_nonce_mac,
    verify_token_signatures,
    verify_webhook_signature,
)

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


# ---------------------------------------------------------------------------
# Enrollment nonce generation / verification
# ---------------------------------------------------------------------------


JWT_SECRET = "test_jwt_secret_key_for_nonce_hmac"


class TestEnrollmentNonce:
    """Nonce generation and stateless HMAC verification."""

    def test_generate_returns_nonce_and_mac(self):
        nonce, mac = generate_enrollment_nonce(JWT_SECRET)

        assert len(nonce) > 20
        assert len(mac) == 64  # SHA-256 hex digest

    def test_nonce_contains_timestamp(self):
        nonce, _ = generate_enrollment_nonce(JWT_SECRET)

        # Format: {random}:{unix_epoch}
        parts = nonce.rsplit(":", 1)
        assert len(parts) == 2
        assert parts[1].isdigit()

    def test_verify_accepts_own_nonce(self):
        nonce, mac = generate_enrollment_nonce(JWT_SECRET)

        assert verify_nonce_mac(nonce, mac, JWT_SECRET) is True

    def test_verify_rejects_wrong_mac(self):
        nonce, _ = generate_enrollment_nonce(JWT_SECRET)

        assert verify_nonce_mac(nonce, "bad_mac_value", JWT_SECRET) is False

    def test_verify_rejects_wrong_secret(self):
        nonce, mac = generate_enrollment_nonce(JWT_SECRET)

        assert verify_nonce_mac(nonce, mac, "different_secret") is False

    def test_verify_rejects_tampered_nonce(self):
        nonce, mac = generate_enrollment_nonce(JWT_SECRET)

        assert verify_nonce_mac(nonce + "x", mac, JWT_SECRET) is False

    def test_verify_rejects_expired_nonce(self):
        """Nonce issued > 5 minutes ago should be rejected."""
        import hmac as hmac_mod
        import hashlib

        expired_nonce = f"faketoken:{int(__import__('time').time()) - 600}"
        expired_mac = hmac_mod.new(
            JWT_SECRET.encode(), expired_nonce.encode(), hashlib.sha256
        ).hexdigest()

        assert verify_nonce_mac(expired_nonce, expired_mac, JWT_SECRET) is False

    def test_nonces_are_unique(self):
        nonce_a, _ = generate_enrollment_nonce(JWT_SECRET)
        nonce_b, _ = generate_enrollment_nonce(JWT_SECRET)

        assert nonce_a != nonce_b


# ---------------------------------------------------------------------------
# Ed25519 token signature verification
# ---------------------------------------------------------------------------


class TestVerifyTokenSignatures:
    """Ed25519 signature verification for Teller enrollment tokens."""

    @staticmethod
    def _generate_keypair() -> tuple[Ed25519PrivateKey, str]:
        """Generate an Ed25519 key pair, return (private_key, public_key_b64)."""
        private_key = Ed25519PrivateKey.generate()
        pub_bytes = private_key.public_key().public_bytes_raw()
        pub_b64 = base64.b64encode(pub_bytes).decode()
        return private_key, pub_b64

    @staticmethod
    def _sign(
        private_key: Ed25519PrivateKey,
        nonce: str,
        access_token: str,
        user_id: str,
        enrollment_id: str,
        environment: str,
    ) -> str:
        """Produce a base64-encoded Ed25519 signature of the enrollment payload."""
        message = f"{nonce}.{access_token}.{user_id}.{enrollment_id}.{environment}"
        sig = private_key.sign(message.encode())
        return base64.b64encode(sig).decode()

    def test_valid_signature_passes(self):
        priv, pub_b64 = self._generate_keypair()
        sig = self._sign(priv, "n1", "tok_abc", "usr_1", "enr_1", "sandbox")

        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=[sig],
            public_key_b64=pub_b64,
        ) is True

    def test_wrong_key_rejects(self):
        priv, _ = self._generate_keypair()
        _, other_pub_b64 = self._generate_keypair()
        sig = self._sign(priv, "n1", "tok_abc", "usr_1", "enr_1", "sandbox")

        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=[sig],
            public_key_b64=other_pub_b64,
        ) is False

    def test_tampered_token_rejects(self):
        priv, pub_b64 = self._generate_keypair()
        sig = self._sign(priv, "n1", "tok_abc", "usr_1", "enr_1", "sandbox")

        assert verify_token_signatures(
            access_token="tok_TAMPERED",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=[sig],
            public_key_b64=pub_b64,
        ) is False

    def test_empty_signatures_rejects(self):
        _, pub_b64 = self._generate_keypair()

        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=[],
            public_key_b64=pub_b64,
        ) is False

    def test_invalid_public_key_rejects(self):
        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=["AAAA"],
            public_key_b64="not_a_valid_key!!!",
        ) is False

    def test_multiple_signatures_one_valid(self):
        """Key rotation: at least one valid signature should pass."""
        priv, pub_b64 = self._generate_keypair()
        good_sig = self._sign(priv, "n1", "tok_abc", "usr_1", "enr_1", "sandbox")

        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="n1",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=["bad_sig_xxxxxxxx", good_sig],
            public_key_b64=pub_b64,
        ) is True

    def test_wrong_nonce_rejects(self):
        priv, pub_b64 = self._generate_keypair()
        sig = self._sign(priv, "original_nonce", "tok_abc", "usr_1", "enr_1", "sandbox")

        assert verify_token_signatures(
            access_token="tok_abc",
            nonce="different_nonce",
            teller_user_id="usr_1",
            enrollment_id="enr_1",
            environment="sandbox",
            signatures=[sig],
            public_key_b64=pub_b64,
        ) is False
