import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

from .config import Paths, private_dir
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
        self.paths.check()
        key, db = self.paths.key.exists(), self.paths.database.exists()
        if key != db:
            raise IncompleteVault(
                "Incomplete vault: both key and database are required. " + RECOVERY
            )
        return key and db

    @contextmanager
    def store_connection(self) -> Iterator[tuple[sqlite3.Connection, Fernet, bool]]:
        """Open a write transaction, creating the schema with the first entry."""
        with _INITIALIZE_LOCK:
            if not self.state():
                with self._initialize() as (db, fernet):
                    yield db, fernet, True
                return
        with self.connection(write=True) as (db, fernet):
            yield db, fernet, False

    @contextmanager
    def _initialize(self) -> Iterator[tuple[sqlite3.Connection, Fernet]]:
        created: list[Path] = []
        commit_started = False
        try:
            private_dir(self.paths.key.parent)
            private_dir(self.paths.database.parent)
            self.keys.create()
            created.append(self.paths.key)
            fd = os.open(
                self.paths.database,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            created.append(self.paths.database)
            os.close(fd)
            with self.connection(write=True, check=False) as (db, fernet):
                db.execute("""
                    CREATE TABLE vault_meta(schema_version INTEGER NOT NULL,
                        key_provider TEXT NOT NULL, encrypted_key_check BLOB NOT NULL,
                        created_at TEXT NOT NULL)
                """)
                db.execute("""
                    CREATE TABLE entries(topic TEXT NOT NULL, environment TEXT NOT NULL,
                        entry_type TEXT NOT NULL CHECK(entry_type IN ('credential','secret')),
                        encrypted_payload BLOB NOT NULL, created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL, PRIMARY KEY(topic, environment))
                """)
                db.execute(
                    "INSERT INTO vault_meta VALUES (1, 'local-file', ?, ?)",
                    (encrypt(fernet, {"v": 1, "kind": "key-check"}), now()),
                )
                yield db, fernet
                commit_started = True
        except (OSError, VaultCorrupt):
            raise IncompleteVault(
                "Initialization interrupted or files inaccessible. " + RECOVERY
            ) from None
        finally:
            # After a commit attempt, preserve files because the outcome may be uncertain.
            if not commit_started:
                for path in reversed(created):
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        break  # Preserve the key if the database could not be removed.

    @contextmanager
    def connection(
        self, *, write: bool = False, check: bool = True
    ) -> Iterator[tuple[sqlite3.Connection, Fernet]]:
        if not self.state():
            raise VaultNotInitialized(
                "Vault does not exist yet. Store the first credential or secret to create it."
            )
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(
                self.paths.database.absolute().as_uri() + "?mode=rw",
                uri=True,
                timeout=10,
                isolation_level=None,
            )
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA secure_delete=ON")
            with db:
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                fernet = self.keys.load()
                if check:
                    rows = db.execute("SELECT * FROM vault_meta").fetchall()
                    if len(rows) != 1:
                        raise VaultCorrupt("Invalid vault metadata.")
                    row = rows[0]
                    if (
                        row["schema_version"] != 1
                        or row["key_provider"] != "local-file"
                    ):
                        raise UnsupportedSchema(
                            "Unsupported vault schema or key provider."
                        )
                    if decrypt(fernet, row["encrypted_key_check"]) != {
                        "v": 1,
                        "kind": "key-check",
                    }:
                        raise VaultCorrupt("Vault key check failed.")
                yield db, fernet
        except sqlite3.Error:
            raise VaultCorrupt(
                "Vault database operation failed; data was not reset."
            ) from None
        finally:
            if db is not None:
                db.close()
