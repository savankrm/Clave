import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest

from clave import (
    BackupError,
    EntryAlreadyExists,
    IncompleteVault,
    Vault,
    VaultCorrupt,
    VaultNotInitialized,
)

PASSPHRASE = "fake archive passphrase"


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


def test_restore_refuses_partial_vault_and_rolls_back_failed_write(
    tmp_path, monkeypatch
):
    source = Vault(tmp_path / "source")
    source.store_secret("token", "fake")
    archive = tmp_path / "backup.clave"
    source.backup(archive, PASSPHRASE)
    restored = Vault(tmp_path / "target")
    paths = restored._storage.paths
    paths.key.parent.mkdir(parents=True)
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
