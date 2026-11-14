import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import Paths, private_dir, safe_path
from .crypto import LocalFileKeyProvider, decrypt, encrypt
from .exceptions import (
    IncompleteVault,
    UnsupportedSchema,
    VaultCorrupt,
    VaultNotInitialized,
)

RECOVERY = "Losing the key or database, or corruption, can make records permanently unrecoverable in V1."
_INITIALIZE_LOCK = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Storage:
    def __init__(self, paths: Paths) -> None:
        self.paths = paths
        self.keys = LocalFileKeyProvider(paths.key)

    def state(self) -> bool:
        safe_path(self.paths.key)
        safe_path(self.paths.database)
        key, db = self.paths.key.exists(), self.paths.database.exists()
        if key != db:
            raise IncompleteVault(
                "Incomplete vault: both key and database are required. " + RECOVERY
            )
        return key and db

    def ensure_initialized(self) -> bool:
        """Create the vault before its first write; return whether it was created."""
        with _INITIALIZE_LOCK:
            if self.state():
                return False
            private_dir(self.paths.key.parent)
            private_dir(self.paths.database.parent)
            try:
                self.keys.create()
                fd = os.open(
                    self.paths.database,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                os.close(fd)
                with self.connection(check=False) as db:
                    db.executescript("""
                        CREATE TABLE vault_meta(schema_version INTEGER NOT NULL,
                            key_provider TEXT NOT NULL, encrypted_key_check BLOB NOT NULL,
                            created_at TEXT NOT NULL);
                        CREATE TABLE entries(topic TEXT NOT NULL, environment TEXT NOT NULL,
                            entry_type TEXT NOT NULL CHECK(entry_type IN ('credential','secret')),
                            encrypted_payload BLOB NOT NULL, created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL, PRIMARY KEY(topic, environment));
                    """)
                    db.execute(
                        "INSERT INTO vault_meta VALUES (1, 'local-file', ?, ?)",
                        (
                            encrypt(self.keys.load(), {"v": 1, "kind": "key-check"}),
                            now(),
                        ),
                    )
                return True
            except (OSError, sqlite3.Error):
                raise IncompleteVault(
                    "Initialization interrupted or files inaccessible; inspect vault files. "
                    + RECOVERY
                ) from None

    @contextmanager
    def connection(self, *, check: bool = True) -> Iterator[sqlite3.Connection]:
        if not self.state():
            raise VaultNotInitialized(
                "Vault does not exist yet. Store the first credential or secret to create it."
            )
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(
                self.paths.database.as_uri() + "?mode=rw", uri=True, timeout=10
            )
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            if check:
                rows = db.execute("SELECT * FROM vault_meta").fetchall()
                if len(rows) != 1:
                    raise VaultCorrupt("Invalid vault metadata.")
                row = rows[0]
                if row["schema_version"] != 1 or row["key_provider"] != "local-file":
                    raise UnsupportedSchema("Unsupported vault schema or key provider.")
                if decrypt(self.keys.load(), row["encrypted_key_check"]) != {
                    "v": 1,
                    "kind": "key-check",
                }:
                    raise VaultCorrupt("Vault key check failed.")
            with db:
                yield db
        except sqlite3.Error:
            raise VaultCorrupt(
                "Vault database operation failed; data was not reset."
            ) from None
        finally:
            if db is not None:
                db.close()
