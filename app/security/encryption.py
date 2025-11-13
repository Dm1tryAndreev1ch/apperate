"""Application-wide encryption utilities."""
from __future__ import annotations

import hashlib
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionService:
    """Wrapper around Fernet symmetric encryption."""

    def __init__(self, secret_key: str):
        try:
            key_bytes = secret_key.encode("utf-8")
            # Ensure key is valid base64 32 bytes
            if len(key_bytes) != 44:
                raise ValueError("Fernet key must be 32 url-safe base64-encoded bytes.")
            self._fernet = Fernet(key_bytes)
        except (ValueError, InvalidToken) as exc:
            raise ValueError("Invalid encryption key configured") from exc

    def encrypt_bytes(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt_bytes(self, token: bytes) -> bytes:
        return self._fernet.decrypt(token)

    def encrypt_text(self, text: str) -> str:
        if text is None:
            return text
        token = self.encrypt_bytes(text.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt_text(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return token
        data = self.decrypt_bytes(token.encode("utf-8"))
        return data.decode("utf-8")

    def encrypt_transport(self, payload: bytes) -> str:
        """Encrypt payload and return base64 string for transport."""
        token = self.encrypt_bytes(payload)
        return base64.urlsafe_b64encode(token).decode("utf-8")

    def decrypt_transport(self, payload: str) -> bytes:
        """Decrypt base64-encoded payload from transport."""
        token = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return self.decrypt_bytes(token)


def _derive_encryption_key() -> str:
    """Ensure we have a valid Fernet key."""
    key = settings.ENCRYPTION_SECRET
    if key:
        return key
    # Derive from SECRET_KEY by hashing
    base = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(base).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return fernet_key.decode("utf-8")


encryption_service = EncryptionService(_derive_encryption_key())


