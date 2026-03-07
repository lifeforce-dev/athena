"""Tests for encryption utilities: Fernet round-trip and certificate handling.

Covers encrypt/decrypt symmetry, key generation, bad-key rejection,
and the temp-file cert decoder.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest
from cryptography.fernet import InvalidToken

from app.common.encryption import (
    decode_cert_to_tempfile,
    decrypt_token,
    encrypt_token,
    generate_fernet_key,
)

# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------


class TestGenerateFernetKey:
    """generate_fernet_key should produce valid, unique Fernet keys."""

    def test_key_is_url_safe_base64(self):
        key = generate_fernet_key()
        # Fernet keys are 44 chars of URL-safe base64 (32 bytes encoded).
        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == 32

    def test_keys_are_unique(self):
        keys = {generate_fernet_key() for _ in range(10)}
        assert len(keys) == 10


# ---------------------------------------------------------------------------
# Encrypt / decrypt round-trip
# ---------------------------------------------------------------------------


class TestEncryptDecryptRoundTrip:
    """Encrypting then decrypting should return the original plaintext."""

    KEY = generate_fernet_key()

    def test_basic_round_trip(self):
        plaintext = "access-token-abc123"
        ciphertext = encrypt_token(plaintext, self.KEY)
        assert decrypt_token(ciphertext, self.KEY) == plaintext

    def test_empty_string_round_trip(self):
        ciphertext = encrypt_token("", self.KEY)
        assert decrypt_token(ciphertext, self.KEY) == ""

    def test_unicode_round_trip(self):
        plaintext = "토큰-값-🔑"
        ciphertext = encrypt_token(plaintext, self.KEY)
        assert decrypt_token(ciphertext, self.KEY) == plaintext

    def test_long_token_round_trip(self):
        plaintext = "x" * 10_000
        ciphertext = encrypt_token(plaintext, self.KEY)
        assert decrypt_token(ciphertext, self.KEY) == plaintext

    def test_wrong_key_raises(self):
        ciphertext = encrypt_token("secret", self.KEY)
        wrong_key = generate_fernet_key()

        with pytest.raises(InvalidToken):
            decrypt_token(ciphertext, wrong_key)

    def test_tampered_ciphertext_raises(self):
        ciphertext = encrypt_token("secret", self.KEY)
        tampered = ciphertext[:-4] + "XXXX"

        with pytest.raises(InvalidToken):
            decrypt_token(tampered, self.KEY)


# ---------------------------------------------------------------------------
# Certificate temp-file decoder
# ---------------------------------------------------------------------------


class TestDecodeCertToTempfile:
    """decode_cert_to_tempfile should write decoded content and return a path."""

    SAMPLE_CERT_CONTENT = b"-----BEGIN CERTIFICATE-----\nMIIBtest...\n-----END CERTIFICATE-----\n"

    def test_creates_pem_file(self):
        b64 = base64.b64encode(self.SAMPLE_CERT_CONTENT).decode()
        path = Path(decode_cert_to_tempfile(b64))

        try:
            assert path.is_file()
            assert path.suffix == ".pem"
        finally:
            path.unlink()

    def test_file_contains_decoded_content(self):
        b64 = base64.b64encode(self.SAMPLE_CERT_CONTENT).decode()
        path = Path(decode_cert_to_tempfile(b64))

        try:
            assert path.read_bytes() == self.SAMPLE_CERT_CONTENT
        finally:
            path.unlink()

    def test_empty_content(self):
        b64 = base64.b64encode(b"").decode()
        path = Path(decode_cert_to_tempfile(b64))

        try:
            assert path.is_file()
            assert path.read_bytes() == b""
        finally:
            path.unlink()
