# -*- coding: utf-8 -*-
"""Fernet-based symmetric encryption for API keys.

The encryption key is derived from the application SECRET_KEY using PBKDF2.
Each call to encrypt() prepends a random IV via Fernet, so the same plaintext
produces a different ciphertext every time — safe to store in DB.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        # Derive a 32-byte key from SECRET_KEY using PBKDF2
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            settings.SECRET_KEY.encode(),
            b"exam-hub-ai-key-encryption",
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(dk)
        _fernet = Fernet(key)
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key. Returns a URL-safe base64 string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> Optional[str]:
    """Decrypt an API key. Returns None if decryption fails."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception) as exc:
        logger.warning("Failed to decrypt API key: %s", type(exc).__name__)
        return None


def sanitize_error(exc: Exception, max_len: int = 200) -> str:
    """Remove potential API keys / Bearer tokens from exception messages."""
    import re
    msg = str(exc)[:max_len]
    # Mask Bearer tokens, sk-* keys, and long base64-like strings after 'key' or 'token'
    msg = re.sub(r'(Bearer\s+)\S+', r'\1***', msg)
    msg = re.sub(r'(sk-[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+', r'\1***', msg)
    msg = re.sub(r'(api[_-]?key[=:\s]+)["\']?[a-zA-Z0-9_-]{8,}["\']?', r'\1***', msg, flags=re.IGNORECASE)
    return msg
