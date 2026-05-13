from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def build_fernet_key(secret: str, explicit_key: str | None = None) -> bytes:
    if explicit_key:
        return explicit_key.encode()
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class SessionCipher:
    def __init__(self, secret_key: str, encryption_key: str | None = None):
        self.fernet = Fernet(build_fernet_key(secret_key, encryption_key))

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        try:
            return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Telegram session shifri ochilmadi") from exc
