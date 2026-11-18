import errno
import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from time import time

import pytest
from cryptography.fernet import Fernet, InvalidToken

from clave import (
    BackupError,
    EntryAlreadyExists,
    IncompleteVault,
    Vault,
    VaultCorrupt,
    VaultNotInitialized,
)

PASSPHRASE = "fake archive passphrase"


def test_rotation_is_due_after_fifteen_days(tmp_path, monkeypatch):
    vault = Vault(tmp_path / "vault")
    vault.store("db.dev", "fake-user", "fake-password")
    vault.store_secret("token", "fake-token")
    paths = vault._storage.paths
    original_key = paths.key.read_bytes()
    original_entries = vault.list()
    cutoff = int(time())
    marker = Fernet(original_key).encrypt_at_time(
        json.dumps({"v": 1, "kind": "key-check"}).encode(), cutoff - 15 * 86400
    )
    with closing(sqlite3.connect(paths.database)) as db, db:
        db.execute("UPDATE vault_meta SET encrypted_key_check=?", (marker,))
    monkeypatch.setattr("clave.storage.time", lambda: cutoff - 1)
    assert vault.get_secret("token") == "fake-token"
    assert paths.key.read_bytes() == original_key

    monkeypatch.setattr("clave.storage.time", lambda: cutoff)
    vault.doctor()
    assert paths.key.read_bytes() == original_key
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(vault.get_secret, ["token"] * 4))
    assert results == ["fake-token"] * 4
    replacement = paths.key.read_bytes()
    assert replacement != original_key
    assert vault.get("db.dev").password == "fake-password"
    assert vault.list() == original_entries
    assert paths.key.read_bytes() == replacement
    with closing(sqlite3.connect(paths.database)) as db:
        payload = db.execute(
            "SELECT encrypted_payload FROM entries LIMIT 1"
        ).fetchone()[0]
    with pytest.raises(InvalidToken):
        Fernet(original_key).decrypt(payload)
    assert not list(paths.key.parent.glob("vault.key.*"))


@pytest.mark.parametrize("phase", ["before-commit", "after-commit"])
def test_rotation_recovers_after_process_termination(tmp_path, phase):
    root = tmp_path / "vault"
    vault = Vault(root)
    vault.store_secret("token", "fake-token")
    key = vault._storage.paths.key
    original = key.read_bytes()
    crash = """
import os
import sys

from clave import Vault
from clave.crypto import LocalFileKeyProvider

def terminate_before_commit(*args):
    os._exit(71)

replace = LocalFileKeyProvider.replace_with

def terminate_after_commit(self, staged):
    if self.path.name == 'vault.key':
        os._exit(71)
    replace(self, staged)

if sys.argv[2] == 'before-commit':
    import clave.storage
    clave.storage.encrypt = terminate_before_commit
else:
    LocalFileKeyProvider.replace_with = terminate_after_commit

Vault(sys.argv[1]).rotate_key()
"""
    process = subprocess.run(
        [sys.executable, "-c", crash, str(root), phase],
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert process.returncode == 71, process.stderr.decode()
    staged = key.with_suffix(".key.next").read_bytes()
    assert key.read_bytes() == original

    assert Vault(root).get_secret("token") == "fake-token"
    expected = original if phase == "before-commit" else staged
    assert key.read_bytes() == expected
    assert not list(key.parent.glob("vault.key.*"))
    vault.rotate_key()
    assert key.read_bytes() != expected
    vault.doctor()


def test_recovery_without_original_key_or_database(tmp_path):
    source = Vault(tmp_path / "source")
    source.store("db.dev", "fake-user", "fake-password")
    source.store_secret("global_token", "fake-global")
    source.store_secret("token.qa", "fake-scoped")
    paths = source._storage.paths
    original_key = paths.key.read_bytes()
    original_entries = source.list()
    archive = tmp_path / "backup.clave"
    source.backup(archive, PASSPHRASE)
    content = archive.read_bytes()
    for private_data in (
        b"fake-password",
        b"fake-user",
        b"global_token",
        b"fake-scoped",
        original_key,
    ):
        assert private_data not in content
    with pytest.raises(BackupError, match="already exists"):
        source.backup(archive, PASSPHRASE)
    assert archive.read_bytes() == content

    paths.key.unlink()
    paths.database.unlink()
    restored = Vault(tmp_path / "restored")
    restored.restore(archive, PASSPHRASE)
    assert restored._storage.paths.key.read_bytes() != original_key
    assert restored.list() == original_entries
    assert restored.get("db.dev").password == "fake-password"
    assert restored.get_secret("global_token") == "fake-global"
    assert restored.get_secret("token.qa") == "fake-scoped"
    restored.doctor()
    with pytest.raises(BackupError, match="vault already exists"):
        restored.restore(archive, PASSPHRASE)
    assert restored.list() == original_entries


def test_invalid_archives_leave_no_vault(tmp_path):
    source = Vault(tmp_path / "source")
    source.store_secret("token", "fake")
    archive = tmp_path / "backup.clave"
    source.backup(archive, PASSPHRASE)
    target = tmp_path / "target"
    restored = Vault(target)
    with pytest.raises(BackupError, match="Could not read"):
        restored.restore(tmp_path / "missing.clave", PASSPHRASE)
    with pytest.raises(BackupError, match="cannot unlock"):
        restored.restore(archive, "wrong archive passphrase")
    archive.write_bytes(archive.read_bytes()[:-14])
    with pytest.raises(BackupError, match="cannot unlock"):
        restored.restore(archive, PASSPHRASE)
    assert not target.exists()


@pytest.mark.parametrize(
    ("operation", "error_code", "message"),
    [
        ("fsync", errno.ENOSPC, "Not enough space"),
        ("link", errno.ENOTSUP, "supports hard links"),
    ],
)
def test_failed_backup_leaves_no_archive_or_changes(
    tmp_path, monkeypatch, operation, error_code, message
):
    vault = Vault(tmp_path / "vault")
    vault.store_secret("token", "fake-original")
    output = tmp_path / "backups"
    output.mkdir()

    def fail(*args):
        raise OSError(error_code, "simulated backup failure")

    with monkeypatch.context() as patch:
        patch.setattr(f"clave.backup.os.{operation}", fail)
        with pytest.raises(BackupError, match=message):
            vault.backup(output / "backup.clave", PASSPHRASE)

    assert list(output.iterdir()) == []
    assert vault.get_secret("token") == "fake-original"
    vault.backup(output / "backup.clave", PASSPHRASE)
    restored = Vault(tmp_path / "restored")
    restored.restore(output / "backup.clave", PASSPHRASE)
    assert restored.get_secret("token") == "fake-original"


def test_restore_refuses_partial_vault_and_rolls_back_failed_write(
    tmp_path, monkeypatch
):
    source = Vault(tmp_path / "source")
    source.store_secret("token", "fake")
    archive = tmp_path / "backup.clave"
    source.backup(archive, PASSPHRASE)
    restored = Vault(tmp_path / "target")
    paths = restored._storage.paths
    paths.roots[0].mkdir(mode=0o700)
    paths.key.parent.mkdir(mode=0o700)
    paths.key.write_bytes(b"original")
    with pytest.raises(IncompleteVault, match="database file is missing"):
        restored.restore(archive, PASSPHRASE)
    assert paths.key.read_bytes() == b"original"
    paths.key.unlink()

    def fail(*args):
        raise OSError("simulated write failure")

    with monkeypatch.context() as patch:
        patch.setattr("clave.crypto.os.fsync", fail)
        with pytest.raises(IncompleteVault):
            restored.restore(archive, PASSPHRASE)
    assert not paths.key.exists()
    assert not paths.database.exists()

    with monkeypatch.context() as patch:
        patch.setattr("clave.vault.encrypt", fail)
        with pytest.raises(IncompleteVault):
            restored.restore(archive, PASSPHRASE)
    assert not paths.key.exists()
    assert not paths.database.exists()
    restored.restore(archive, PASSPHRASE)
    assert restored.get_secret("token") == "fake"


def test_doctor_is_read_only_and_reports_corruption(tmp_path):
    root = tmp_path / "vault"
    vault = Vault(root)
    with pytest.raises(VaultNotInitialized, match="Save your first"):
        vault.doctor()
    assert not root.exists()
    vault.store_secret("token", "fake")
    paths = vault._storage.paths
    database = paths.database.read_bytes()
    key = paths.key.read_bytes()
    vault.doctor()
    assert paths.database.read_bytes() == database
    assert paths.key.read_bytes() == key
    if os.name != "nt":
        paths.key.chmod(0o644)
        with pytest.raises(IncompleteVault, match="permissions are too broad"):
            vault.doctor()
        paths.key.chmod(0o600)
    with closing(sqlite3.connect(paths.database)) as db, db:
        db.execute("UPDATE entries SET encrypted_payload=?", (b"invalid",))
    with pytest.raises(VaultCorrupt):
        vault.doctor()
    archive = tmp_path / "backup.clave"
    with pytest.raises(VaultCorrupt):
        vault.backup(archive, PASSPHRASE)
    assert not archive.exists()


def test_concurrent_create_without_replacement(tmp_path):
    vault = Vault(tmp_path)
    vault.store_secret("existing", "fake")

    def write(value):
        try:
            vault.store_secret("contested", value, allow_replace=False)
        except EntryAlreadyExists:
            return None
        return value

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["first", "second"]))
    winners = [value for value in results if value is not None]
    assert winners == [vault.get_secret("contested")]
