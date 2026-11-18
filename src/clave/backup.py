"""Versioned, authenticated archives protected by a separate passphrase."""

import base64
import errno
import os
import stat
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .config import safe_path
from .crypto import decrypt, encrypt
from .exceptions import BackupError, VaultCorrupt

_HEADER = b"CLAVE-BACKUP-1\n"
_SALT_SIZE = 16


def _cipher(passphrase: str, salt: bytes) -> Fernet:
    key = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(
        passphrase.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(key))


def write_archive(path: Path, passphrase: str, entries: list[dict[str, Any]]) -> None:
    if len(passphrase.strip()) < 12:
        raise BackupError("Use a backup passphrase of at least 12 characters.")
    safe_path(path)
    if path.exists():
        raise BackupError("A file already exists at the backup destination.")
    salt = os.urandom(_SALT_SIZE)
    token = encrypt(
        _cipher(passphrase, salt), {"v": 1, "kind": "backup", "entries": entries}
    )
    try:
        fd, name = tempfile.mkstemp(
            prefix=".clave-backup-", suffix=".enc", dir=path.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(_HEADER)
                stream.write(salt)
                stream.write(token)
                stream.flush()
                os.fsync(stream.fileno())
            # Publish the complete archive in one step without replacing any file.
            os.link(temporary, path)
        finally:
            with suppress(OSError):
                temporary.unlink()
    except FileExistsError:
        raise BackupError("A file already exists at the backup destination.") from None
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            raise BackupError(
                "Not enough space to write the backup. Free some space or choose another folder."
            ) from None
        raise BackupError(
            "Could not write the backup. Choose a writable folder on a filesystem "
            "that supports hard links."
        ) from None


def read_archive(path: Path, passphrase: str) -> list[Any]:
    safe_path(path)
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            raise BackupError("Choose a regular Clave backup file.")
        content = path.read_bytes()
    except OSError:
        raise BackupError(
            "Could not read the backup file. Check its path and permissions."
        ) from None
    body = content.removeprefix(_HEADER)
    if len(body) == len(content) or len(body) <= _SALT_SIZE:
        raise BackupError("The file is not a supported Clave backup.")
    salt, token = body[:_SALT_SIZE], body[_SALT_SIZE:]
    try:
        payload = decrypt(_cipher(passphrase, salt), token)
    except VaultCorrupt:
        raise BackupError(
            "Clave cannot unlock the backup. Check the passphrase or use another copy."
        ) from None
    entries = payload.get("entries")
    if payload.get("kind") != "backup" or not isinstance(entries, list):
        raise BackupError("Invalid Clave backup contents.")
    return entries
