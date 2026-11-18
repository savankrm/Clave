import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .backup import read_archive, write_archive
from .config import Paths
from .crypto import decrypt, encrypt
from .exceptions import (
    BackupError,
    EntryAlreadyExists,
    EntryNotFound,
    EntryTypeMismatch,
    InvalidIdentifier,
    VaultCorrupt,
)
from .identifiers import environment, identifier, nonblank, secret_identifier
from .models import Credential, EntryMetadata, EntryType, StoreResult
from .storage import Storage, now


class Vault:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._storage = Storage(Paths.resolve(data_dir))

    @staticmethod
    def _address(entry_id: str, kind: EntryType) -> tuple[str, str]:
        if kind == "secret":
            return secret_identifier(entry_id)
        return identifier(entry_id)

    @staticmethod
    def _check_payload(payload: dict[str, Any], kind: EntryType) -> None:
        fields = ("username", "password") if kind == "credential" else ("value",)
        if (
            payload.get("v") != 1
            or payload.get("kind") != kind
            or any(
                not isinstance(payload.get(key), str) or not payload[key].strip()
                for key in fields
            )
        ):
            raise VaultCorrupt("Invalid encrypted entry payload.")

    def _read(self, entry_id: str, kind: EntryType) -> dict[str, Any]:
        topic, env = self._address(entry_id, kind)
        with self._storage.connection() as (db, fernet):
            row = db.execute(
                "SELECT * FROM entries WHERE topic=? AND environment=?", (topic, env)
            ).fetchone()
            if row is None:
                raise EntryNotFound("Entry does not exist.")
            if row["entry_type"] != kind:
                raise EntryTypeMismatch("Entry has a different type.")
            payload = decrypt(fernet, row["encrypted_payload"])
            self._check_payload(payload, kind)
            return payload

    def get(self, id: str) -> Credential:
        payload = self._read(id, "credential")
        return Credential(payload["username"], payload["password"])

    def get_secret(self, id: str) -> str:
        return str(self._read(id, "secret")["value"])

    def _write(
        self,
        entry_id: str,
        kind: EntryType,
        payload: dict[str, Any],
        *,
        allow_replace: bool,
    ) -> StoreResult:
        topic, env = self._address(entry_id, kind)
        with self._storage.store_connection() as (db, fernet, vault_created):
            row = db.execute(
                "SELECT entry_type FROM entries WHERE topic=? AND environment=?",
                (topic, env),
            ).fetchone()
            if row is not None and row["entry_type"] != kind:
                raise EntryTypeMismatch("Entry has a different type.")
            if row is not None and not allow_replace:
                raise EntryAlreadyExists("Entry already exists.")
            token = encrypt(fernet, {"v": 1, "kind": kind, **payload})
            timestamp = now()
            db.execute(
                """INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic, environment) DO UPDATE SET
                encrypted_payload=excluded.encrypted_payload, updated_at=excluded.updated_at""",
                (topic, env, kind, token, timestamp, timestamp),
            )
            return StoreResult(
                "created" if row is None else "replaced",
                vault_created=vault_created,
            )

    def store(
        self, id: str, username: str, password: str, *, allow_replace: bool = True
    ) -> StoreResult:
        nonblank(username)
        nonblank(password)
        return self._write(
            id,
            "credential",
            {"username": username, "password": password},
            allow_replace=allow_replace,
        )

    def store_secret(
        self, id: str, value: str, *, allow_replace: bool = True
    ) -> StoreResult:
        nonblank(value)
        return self._write(id, "secret", {"value": value}, allow_replace=allow_replace)

    def _check_snapshot_entry(self, entry: Any) -> tuple[str, str]:
        if not isinstance(entry, dict):
            raise VaultCorrupt("Invalid vault entry.")
        topic, env, kind = (
            entry.get("topic"),
            entry.get("environment"),
            entry.get("entry_type"),
        )
        if (
            not isinstance(topic, str)
            or not isinstance(env, str)
            or kind not in ("credential", "secret")
        ):
            raise VaultCorrupt("Invalid vault entry metadata.")
        try:
            address = self._address(f"{topic}.{env}" if env else topic, kind)
            if address != (topic, env):
                raise ValueError
            datetime.fromisoformat(entry["created_at"])
            datetime.fromisoformat(entry["updated_at"])
        except (InvalidIdentifier, KeyError, TypeError, ValueError):
            raise VaultCorrupt("Invalid vault entry metadata.") from None
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            raise VaultCorrupt("Invalid encrypted entry payload.")
        self._check_payload(payload, kind)
        return address

    def _snapshot_entries(
        self, db: sqlite3.Connection, fernet: Fernet
    ) -> Iterator[dict[str, Any]]:
        rows = db.execute(
            "SELECT topic, environment, entry_type, encrypted_payload, created_at, "
            "updated_at FROM entries ORDER BY topic, environment"
        )
        for row in rows:
            entry = dict(row)
            entry["payload"] = decrypt(fernet, entry.pop("encrypted_payload"))
            self._check_snapshot_entry(entry)
            yield entry

    def doctor(self) -> None:
        """Check vault integrity and permissions without changing stored data."""
        with self._storage.connection() as (db, fernet):
            if [row[0] for row in db.execute("PRAGMA integrity_check")] != ["ok"]:
                raise VaultCorrupt("Vault database failed its integrity check.")
            for _ in self._snapshot_entries(db, fernet):
                pass

    def backup(self, path: str | Path, passphrase: str) -> None:
        """Write a consistent copy encrypted with a separate backup passphrase."""
        with self._storage.connection() as (db, fernet):
            entries = list(self._snapshot_entries(db, fernet))
        write_archive(Path(path), passphrase, entries)

    def restore(self, path: str | Path, passphrase: str) -> None:
        """Restore an archive into a fresh vault using a newly generated local key."""
        entries = read_archive(Path(path), passphrase)
        seen = set()
        try:
            for entry in entries:
                address = self._check_snapshot_entry(entry)
                if address in seen:
                    raise BackupError("The backup contains duplicate entries.")
                seen.add(address)
        except VaultCorrupt:
            raise BackupError("The backup contains invalid entries.") from None
        with self._storage.store_connection() as (db, fernet, created):
            if not created:
                raise BackupError(
                    "A vault already exists here. Choose a fresh location."
                )
            db.executemany(
                "INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        entry["topic"],
                        entry["environment"],
                        entry["entry_type"],
                        encrypt(fernet, entry["payload"]),
                        entry["created_at"],
                        entry["updated_at"],
                    )
                    for entry in entries
                ),
            )

    def find(self, query: str, *, env: str | None = None) -> list[EntryMetadata]:
        """Find entry names by case-insensitive substring."""
        nonblank(query)
        term = query.strip().casefold()
        return [entry for entry in self.list(env) if term in entry.id.casefold()]

    def list(self, env: str | None = None) -> list[EntryMetadata]:
        if env is not None:
            environment(env)
        with self._storage.connection() as (db, _):
            rows = db.execute(
                "SELECT topic, environment, entry_type, created_at, updated_at FROM entries"
                + (" WHERE environment=?" if env is not None else "")
                + " ORDER BY topic, environment",
                (env,) if env is not None else (),
            ).fetchall()
            return [
                EntryMetadata(
                    (
                        r["topic"]
                        if r["entry_type"] == "secret" and not r["environment"]
                        else f"{r['topic']}.{r['environment']}"
                    ),
                    r["environment"] or None,
                    r["entry_type"],
                    r["created_at"],
                    r["updated_at"],
                )
                for r in rows
            ]

    def delete(self, id: str) -> None:
        topic, env = secret_identifier(id)
        with self._storage.connection(write=True) as (db, _):
            if (
                db.execute(
                    "DELETE FROM entries WHERE topic=? AND environment=?", (topic, env)
                ).rowcount
                == 0
            ):
                raise EntryNotFound("Entry does not exist.")
