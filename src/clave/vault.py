from pathlib import Path
from typing import Any

from .config import Paths
from .crypto import decrypt, encrypt
from .exceptions import EntryNotFound, EntryTypeMismatch, VaultCorrupt
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
            fields = ("username", "password") if kind == "credential" else ("value",)
            if payload.get("kind") != kind or any(
                not isinstance(payload.get(k), str) or not payload[k].strip()
                for k in fields
            ):
                raise VaultCorrupt("Invalid encrypted entry payload.")
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
    ) -> StoreResult:
        topic, env = self._address(entry_id, kind)
        with self._storage.store_connection() as (db, fernet, vault_created):
            row = db.execute(
                "SELECT entry_type FROM entries WHERE topic=? AND environment=?",
                (topic, env),
            ).fetchone()
            if row is not None and row["entry_type"] != kind:
                raise EntryTypeMismatch("Entry has a different type.")
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

    def store(self, id: str, username: str, password: str) -> StoreResult:
        nonblank(username)
        nonblank(password)
        return self._write(
            id, "credential", {"username": username, "password": password}
        )

    def store_secret(self, id: str, value: str) -> StoreResult:
        nonblank(value)
        return self._write(id, "secret", {"value": value})

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
