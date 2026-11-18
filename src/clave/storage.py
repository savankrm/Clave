import os
import sqlite3
import stat
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import time

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from .config import Paths, private_dir
from .crypto import LocalFileKeyProvider, decrypt, encrypt
from .exceptions import (
    IncompleteVault,
    UnsupportedSchema,
    VaultCorrupt,
    VaultNotInitialized,
)

RECOVERY = "Keep an encrypted backup and its passphrase somewhere safe."
_INITIALIZE_LOCK = threading.Lock()
_KEY_CHECK = {"v": 1, "kind": "key-check"}
_ROTATION_INTERVAL = 15 * 24 * 60 * 60


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Storage:
    def __init__(self, paths: Paths) -> None:
        self.paths = paths
        self.keys = LocalFileKeyProvider(paths.key)
        self._next_key = LocalFileKeyProvider(paths.key.with_suffix(".key.next"))
        self._key_draft = LocalFileKeyProvider(paths.key.with_suffix(".key.draft"))

    def state(self) -> bool:
        self.paths.check()
        present = []
        for label, path in (("key", self.paths.key), ("database", self.paths.database)):
            try:
                mode = path.stat().st_mode
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(mode):
                raise IncompleteVault(f"The vault {label} must be a regular file.")
            present.append(label)
        if len(present) == 1:
            missing = "database" if present[0] == "key" else "key"
            raise IncompleteVault(
                f"Incomplete vault: the {missing} file is missing. "
                "Check the selected vault or restore a backup to a fresh location."
            )
        return bool(present)

    def _check_permissions(self, *, include_files: bool = True) -> None:
        if os.name == "nt":
            return
        paths = self.paths
        private_paths = (*paths.roots, paths.key.parent, paths.database.parent)
        if include_files:
            private_paths += (paths.key, paths.database)
        for path in private_paths:
            if path.stat().st_mode & 0o077:
                raise IncompleteVault(
                    f"Vault permissions are too broad on {path.name}. "
                    "Use chmod go-rwx on that vault path, then run clave doctor."
                )

    @contextmanager
    def store_connection(
        self, *, rotate_due: bool = True
    ) -> Iterator[tuple[sqlite3.Connection, Fernet, bool]]:
        """Open a write transaction, creating the schema with the first entry."""
        with _INITIALIZE_LOCK:
            if not self.state():
                with self._initialize() as (db, fernet):
                    yield db, fernet, True
                return
        with self.connection(write=True, rotate_due=rotate_due) as (db, fernet):
            yield db, fernet, False

    @contextmanager
    def _initialize(self) -> Iterator[tuple[sqlite3.Connection, Fernet]]:
        created: list[Path] = []
        commit_started = False
        try:
            private_dir(self.paths.key.parent)
            private_dir(self.paths.database.parent)
            self._check_permissions(include_files=False)
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
                    (encrypt(fernet, _KEY_CHECK), now()),
                )
                yield db, fernet
                commit_started = True
        except (OSError, VaultCorrupt):
            raise IncompleteVault(
                "Initialization interrupted or files inaccessible. "
                "Check vault permissions or try a fresh location."
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
        self, *, write: bool = False, check: bool = True, rotate_due: bool = True
    ) -> Iterator[tuple[sqlite3.Connection, Fernet]]:
        if check and self._has_staged_key():
            self._rotate_key(force=False, rotate_due=rotate_due)
        with self._connection(write=write, check=check) as (
            db,
            fernet,
            marker,
            pending,
        ):
            if not pending and not (rotate_due and self._rotation_due(fernet, marker)):
                yield db, fernet
                return
        self._rotate_key(force=False, rotate_due=rotate_due)
        with self._connection(write=write) as (db, fernet, _, _):
            yield db, fernet

    def rotate_key(self) -> None:
        self._rotate_key(force=True, rotate_due=True)

    def _has_staged_key(self) -> bool:
        return self._next_key.exists() or self._key_draft.exists()

    @staticmethod
    def _rotation_due(fernet: Fernet, marker: bytes | None) -> bool:
        return marker is not None and time() >= (
            fernet.extract_timestamp(marker) + _ROTATION_INTERVAL
        )

    def _rotate_key(self, *, force: bool, rotate_due: bool) -> None:
        try:
            with self._connection(write=True, exclusive=True) as (
                db,
                current,
                marker,
                pending,
            ):
                if self._key_draft.exists():
                    self._key_draft.path.unlink()
                if pending:
                    # SQLite committed in the previous run. Finish publishing its key.
                    self.keys.replace_with(self._next_key)
                    return
                if self._next_key.exists():
                    # SQLite rolled back. The original key still matches the vault.
                    self._next_key.path.unlink()
                if not force and not (
                    rotate_due and self._rotation_due(current, marker)
                ):
                    return

                self._key_draft.create()
                self._next_key.replace_with(self._key_draft)
                replacement = self._next_key.load()
                rotator = MultiFernet([replacement, current])
                rows = db.execute(
                    "SELECT rowid, encrypted_payload FROM entries"
                ).fetchall()
                db.executemany(
                    "UPDATE entries SET encrypted_payload=? WHERE rowid=?",
                    ((rotator.rotate(row[1]), row[0]) for row in rows),
                )
                db.execute(
                    "UPDATE vault_meta SET encrypted_key_check=?",
                    (encrypt(replacement, _KEY_CHECK),),
                )
            # The committed marker can select the staged key while we reacquire the lock.
            with self._connection(write=True, exclusive=True) as (_, _, _, pending):
                if pending:
                    self.keys.replace_with(self._next_key)
        except InvalidToken:
            raise VaultCorrupt(
                "Key rotation stopped because an entry could not be unlocked."
            ) from None
        except OSError:
            raise IncompleteVault(
                "Could not finish vault key rotation. Keep the vault files and try again."
            ) from None

    def _key_for_marker(self, marker: bytes) -> tuple[Fernet, bool]:
        fernet = self.keys.load()
        try:
            if decrypt(fernet, marker) == _KEY_CHECK:
                return fernet, False
        except VaultCorrupt:
            pass
        if self._next_key.exists():
            fernet = self._next_key.load()
            try:
                if decrypt(fernet, marker) == _KEY_CHECK:
                    return fernet, True
            except VaultCorrupt:
                pass
        raise VaultCorrupt(
            "Clave cannot unlock this vault. Check that the key and database belong together."
        )

    @contextmanager
    def _connection(
        self, *, write: bool, check: bool = True, exclusive: bool = False
    ) -> Iterator[tuple[sqlite3.Connection, Fernet, bytes | None, bool]]:
        if not self.state():
            raise VaultNotInitialized(
                "No vault found. Save your first credential or secret to create one."
            )
        self._check_permissions()
        db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(
                self.paths.database.absolute().as_uri()
                + ("?mode=rw" if write else "?mode=ro"),
                uri=True,
                timeout=10,
                isolation_level=None,
            )
            db.row_factory = sqlite3.Row
            if write:
                db.execute("PRAGMA secure_delete=ON")
            if exclusive:
                db.execute("PRAGMA synchronous=EXTRA")
            with db:
                if exclusive:
                    db.execute("BEGIN EXCLUSIVE")
                    if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
                        raise IncompleteVault(
                            "Vault key rotation requires SQLite's default journal mode."
                        )
                else:
                    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                if check:
                    rows = db.execute(
                        "SELECT schema_version, key_provider, encrypted_key_check FROM vault_meta"
                    ).fetchall()
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
                    marker = row["encrypted_key_check"]
                    fernet, pending = self._key_for_marker(marker)
                    yield db, fernet, marker, pending
                else:
                    yield db, self.keys.load(), None, False
        except sqlite3.Error:
            raise VaultCorrupt(
                "Vault database operation failed; data was not reset."
            ) from None
        finally:
            if db is not None:
                db.close()
