from __future__ import annotations

import json
import os
import stat
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

from cryptography.fernet import Fernet, InvalidToken

from .config import safe_path
from .exceptions import IncompleteVault, VaultCorrupt


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

    def exists(self) -> bool:
        safe_path(self.path)
        try:
            mode = self.path.stat().st_mode
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(mode) or (os.name != "nt" and mode & 0o077):
            raise IncompleteVault(
                "The staged vault key must be a private regular file."
            )
        return True

    def sync_parent(self) -> None:
        if os.name != "nt":
            fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def replace_with(self, staged: LocalFileKeyProvider) -> None:
        safe_path(self.path)
        safe_path(staged.path)
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            move = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
            move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
            move.restype = wintypes.BOOL
            replace_existing, write_through = 0x1, 0x8
            if not move(
                str(staged.path), str(self.path), replace_existing | write_through
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            staged.path.replace(self.path)
        self.sync_parent()


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
