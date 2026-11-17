import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from cryptography.fernet import Fernet, InvalidToken

from .config import safe_path
from .exceptions import VaultCorrupt


class LocalFileKeyProvider:
    """Replaceable local-key seam; no provider registry in V1."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def create(self) -> None:
        safe_path(self.path)
        key = Fernet.generate_key()
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(key)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            with suppress(OSError):
                self.path.unlink()
            raise

    def load(self) -> Fernet:
        safe_path(self.path)
        try:
            return Fernet(self.path.read_bytes())
        except (ValueError, OSError):
            raise VaultCorrupt(
                "Cannot read a valid vault key; no key was regenerated."
            ) from None


def encrypt(fernet: Fernet, payload: dict[str, Any]) -> bytes:
    return fernet.encrypt(json.dumps(payload, ensure_ascii=True).encode("utf-8"))


def decrypt(fernet: Fernet, token: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(fernet.decrypt(token))
        if not isinstance(payload, dict) or payload.get("v") != 1:
            raise ValueError
        return cast(dict[str, Any], payload)
    except (InvalidToken, ValueError, TypeError, UnicodeError):
        raise VaultCorrupt(
            "Vault authentication or payload validation failed."
        ) from None
