"""Encryption utilities for Teller access token storage and mTLS certificate handling."""

from __future__ import annotations

import base64
import os
import tempfile

from cryptography.fernet import Fernet


def encrypt_token(plaintext: str, key: str) -> str:
    """Encrypt an access token for database storage."""
    fernet = Fernet(key.encode())
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, key: str) -> str:
    """Decrypt an access token for API calls."""
    fernet = Fernet(key.encode())
    return fernet.decrypt(ciphertext.encode()).decode()


def generate_fernet_key() -> str:
    """Generate a new Fernet key (URL-safe base64-encoded 32 bytes)."""
    return Fernet.generate_key().decode()


def decode_cert_to_tempfile(b64_content: str) -> str:
    """Decode a base64-encoded certificate to a temp file, return its path.

    Sets 0o600 permissions (owner read/write only).
    Caller is responsible for calling os.unlink() on shutdown.
    """
    content = base64.b64decode(b64_content)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    tmp.write(content)
    tmp.close()
    os.chmod(tmp.name, 0o600)
    return tmp.name
