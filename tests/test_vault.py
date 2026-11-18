import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from cryptography.fernet import Fernet

from clave import Vault
from clave.exceptions import (
    EntryNotFound,
    EntryTypeMismatch,
    IncompleteVault,
    InvalidIdentifier,
    InvalidValue,
    UnsafePath,
    UnsupportedSchema,
    VaultCorrupt,
    VaultNotInitialized,
)


@pytest.fixture
def vault(tmp_path):
    return Vault(tmp_path)


def test_api(vault):
    result = vault.store("db.dev", "fake-user", "fake-password")
    assert result.action == "created"
    assert result.vault_created is True
    original = vault.list()[0]
    assert vault.get("db.dev").password == "fake-password"
    assert "fake" not in repr(vault.get("db.dev"))
    assert vault.store("db.dev", "other-user", "other-password").action == "replaced"
    assert vault.list()[0].created_at == original.created_at
    assert vault.list()[0].updated_at != original.updated_at
    assert vault.store("db.dev", "last-user", "last-password").action == "replaced"
    assert vault.get("db.dev").username == "last-user"
    vault.store_secret("api_token", "fake-token")
    assert vault.store_secret("api_token", "replacement").action == "replaced"
    vault.store_secret("api_token", "updated")
    assert vault.get_secret("api_token") == "updated"
    vault.store_secret("regional_token.qa", "regional")
    assert vault.get_secret("regional_token.qa") == "regional"
    secret_metadata = next(
        entry for entry in vault.list() if entry.entry_type == "secret"
    )
    assert secret_metadata.id == "api_token"
    assert secret_metadata.environment is None
    assert len(vault.list("dev")) == 1
    assert [entry.id for entry in vault.list("qa")] == ["regional_token.qa"]
    assert vault.list("DEV") == []
    with pytest.raises(InvalidIdentifier):
        vault.list("bad env")
    vault.delete("api_token")
    with pytest.raises(EntryNotFound):
        vault.delete("api_token")


def test_collisions(vault):
    vault.store_secret("x", "original")
    vault.store("x.dev", "u", "p")
    assert vault.get_secret("x") == "original"
    assert vault.get("x.dev").username == "u"
    with pytest.raises(InvalidIdentifier):
        vault.store("x", "u", "p")
    vault.store("y.dev", "u", "p")
    with pytest.raises(EntryTypeMismatch):
        vault.get_secret("y.dev")
    with pytest.raises(EntryTypeMismatch):
        vault.store_secret("y.dev", "wrong-type")
    vault.store_secret("z.qa", "scoped-secret")
    with pytest.raises(EntryTypeMismatch):
        vault.store("z.qa", "u", "p")
    for call in [
        lambda: vault.get("missing.dev"),
    ]:
        with pytest.raises(EntryNotFound):
            call()


@pytest.mark.parametrize("value", ["", " ", "\n", None, 3])
def test_blank(vault, value):
    with pytest.raises(InvalidValue):
        vault.store_secret("x", value)


def test_invalid_first_store_does_not_create_vault(tmp_path):
    vault = Vault(tmp_path)
    with pytest.raises(InvalidIdentifier):
        vault.store_secret("bad.identifier.extra", "fake")
    with pytest.raises(InvalidValue):
        vault.store_secret("valid", " ")
    assert not vault._storage.paths.key.exists()
    assert not vault._storage.paths.database.exists()


def test_init_states(tmp_path):
    v = Vault(tmp_path)
    with pytest.raises(VaultNotInitialized):
        v.list()
    assert v.store_secret("first", "fake").vault_created is True
    assert v.store_secret("second", "fake").vault_created is False
    key = v._storage.paths.key
    key.unlink()
    with pytest.raises(IncompleteVault):
        v.store_secret("third", "fake")
    with pytest.raises(IncompleteVault):
        v.get_secret("x")
    key.write_bytes(Fernet.generate_key())
    key.chmod(0o600)
    with pytest.raises(VaultCorrupt):
        v.list()
    key.write_bytes(b"invalid")
    with pytest.raises(VaultCorrupt):
        v.list()
    v._storage.paths.database.unlink()
    with pytest.raises(IncompleteVault):
        v.store_secret("third", "fake")


def test_encryption_and_tampering(vault):
    vault.store("x.dev", "unique-fake-username", "unique-fake-password")
    path = vault._storage.paths.database
    content = path.read_bytes()
    assert b"unique-fake-username" not in content
    assert b"unique-fake-password" not in content
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE entries SET encrypted_payload=?", (b"bad-token",))
    with pytest.raises(VaultCorrupt):
        vault.get("x.dev")
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE vault_meta SET schema_version=99")
    with pytest.raises(UnsupportedSchema):
        vault.list()


def test_corrupt_metadata(vault):
    vault.store_secret("first", "fake")
    with closing(sqlite3.connect(vault._storage.paths.database)) as db, db:
        db.execute("DELETE FROM vault_meta")
    with pytest.raises(VaultCorrupt):
        vault.list()


def test_database_corruption(vault):
    vault.store_secret("first", "fake")
    vault._storage.paths.database.write_bytes(b"not sqlite")
    with pytest.raises(VaultCorrupt):
        vault.list()


def test_failed_overwrite(vault, monkeypatch):
    vault.store_secret("x", "original")

    def fail(*args, **kwargs):
        raise OSError("simulated write failure")

    with monkeypatch.context() as patch:
        patch.setattr("clave.vault.encrypt", fail)
        with pytest.raises(OSError):
            vault.store_secret("x", "replacement")
    assert vault.get_secret("x") == "original"
    with closing(sqlite3.connect(vault._storage.paths.database)) as db, db:
        db.execute(
            "CREATE TRIGGER fail_update BEFORE UPDATE ON entries BEGIN SELECT RAISE(ABORT, 'simulated'); END"
        )
    with pytest.raises(VaultCorrupt):
        vault.store_secret("x", "replacement")
    assert vault.get_secret("x") == "original"


def test_concurrency(vault):
    def write(i):
        vault.store_secret("shared", f"fake-{i}")
        return vault.get_secret("shared")

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(x.startswith("fake-") for x in pool.map(write, range(24)))
    assert len(vault.list()) == 1

    def collide(kind):
        try:
            if kind:
                vault.store("collision.dev", "u", "p")
            else:
                vault.store_secret("collision.dev", "v")
            return True
        except EntryTypeMismatch:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(collide, [True, False])) == 1


def test_concurrent_first_stores_across_vault_instances(tmp_path):
    def write(i):
        instance = Vault(tmp_path)
        return instance.store_secret(f"item{i}", f"fake-{i}")

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(write, range(12)))
    assert sum(result.vault_created for result in results) == 1
    assert len(Vault(tmp_path).list()) == 12


def test_independent_random_keys(tmp_path):
    a, b = Vault(tmp_path / "a"), Vault(tmp_path / "b")
    a.store_secret("first", "fake-a")
    b.store_secret("first", "fake-b")
    assert a._storage.paths.key.read_bytes() != b._storage.paths.key.read_bytes()


@pytest.mark.parametrize("location", ["root", "directory", "file", "ancestor"])
def test_symlink(tmp_path, monkeypatch, location):
    target = tmp_path / "target"
    target.mkdir()
    root = tmp_path / "vault"
    link = {
        "root": root,
        "directory": root / "config",
        "file": root / "data" / "vault.sqlite3",
        "ancestor": tmp_path / "alias",
    }[location]
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not permitted by OS")
    if location == "ancestor":
        monkeypatch.setattr(
            "clave.config.user_data_path", lambda *a, **kw: link / "clave"
        )
        monkeypatch.setattr(
            "clave.config.user_config_path", lambda *a, **kw: link / "clave"
        )
        vault = Vault()
        vault.store_secret("first", "fake")
        assert Vault(target / "clave").get_secret("first") == "fake"
    else:
        with pytest.raises(UnsafePath):
            Vault(root).store_secret("first", "fake")


def test_default_paths_do_not_touch_user_files(tmp_path, monkeypatch):
    from clave.config import Paths

    monkeypatch.setattr("clave.config.user_data_path", lambda *a, **k: tmp_path)
    monkeypatch.setattr("clave.config.user_config_path", lambda *a, **k: tmp_path)
    paths = Paths.resolve(None)
    assert paths.key.parent != paths.database.parent
    assert not paths.key.exists()
    monkeypatch.setattr(
        "clave.config.user_config_path", lambda *a, **k: tmp_path / "other"
    )
    assert Paths.resolve(None).key == tmp_path / "other" / "vault.key"


def test_authenticated_malformed_payload(vault):
    from clave.crypto import encrypt

    vault.store_secret("x", "fake")
    fernet = vault._storage.keys.load()
    tokens = [
        fernet.encrypt(b"not json"),
        fernet.encrypt(b"[]"),
        encrypt(fernet, {"v": 99, "kind": "secret", "value": "fake"}),
        encrypt(fernet, {"v": 1, "kind": "secret", "value": 42}),
        encrypt(fernet, {"v": 1, "kind": "credential", "value": "fake"}),
    ]
    for token in tokens:
        with closing(sqlite3.connect(vault._storage.paths.database)) as db, db:
            db.execute("UPDATE entries SET encrypted_payload=?", (token,))
        with pytest.raises(VaultCorrupt):
            vault.get_secret("x")
    with closing(sqlite3.connect(vault._storage.paths.database)) as db, db:
        db.execute(
            "UPDATE vault_meta SET encrypted_key_check=?",
            (encrypt(fernet, {"v": 1, "kind": "wrong"}),),
        )
    with pytest.raises(VaultCorrupt):
        vault.list()


def test_interrupted_init(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("simulated interruption")

    instance = Vault(tmp_path)
    monkeypatch.setattr("clave.storage.os.open", fail)
    with pytest.raises(IncompleteVault):
        instance.store_secret("first", "fake")


def test_first_store_failure_rolls_back_schema_and_can_retry(vault, monkeypatch):
    paths = vault._storage.paths

    def fail(*args):
        with closing(sqlite3.connect(paths.database)) as observer:
            tables = observer.execute("SELECT name FROM sqlite_master").fetchall()
        assert tables == []
        raise OSError("simulated first-entry failure")

    with monkeypatch.context() as patch:
        patch.setattr("clave.vault.encrypt", fail)
        with pytest.raises(IncompleteVault):
            vault.store_secret("first", "fake")

    assert not paths.key.exists()
    assert not paths.database.exists()
    assert vault.store_secret("first", "fake").vault_created
    assert vault.get_secret("first") == "fake"


def test_vault_loads_key_once_per_operation(vault, monkeypatch):
    load = vault._storage.keys.load
    calls = []

    def counted_load():
        calls.append(None)
        return load()

    monkeypatch.setattr(vault._storage.keys, "load", counted_load)
    assert vault.store_secret(id="first", value="one").vault_created
    assert len(calls) == 1
    vault.store_secret(id="first", value="two")
    assert len(calls) == 2
    assert vault.get_secret(id="first") == "two"
    assert len(calls) == 3


def test_relative_vault_path_with_uri_characters(tmp_path, monkeypatch):
    import os

    monkeypatch.chdir(tmp_path)
    root = "vault # 100%" if os.name == "nt" else "vault #? 100%"
    assert Vault(root).store_secret("first", "fake").vault_created
    assert Vault(root).get_secret("first") == "fake"


def test_key_exclusive_creation(vault):
    vault.store_secret("first", "fake")
    original = vault._storage.paths.key.read_bytes()
    with pytest.raises(FileExistsError):
        vault._storage.keys.create()
    assert vault._storage.paths.key.read_bytes() == original


def test_posix_permissions(vault):
    import os
    import stat

    if os.name == "nt":
        pytest.skip("POSIX modes are not a Windows ACL guarantee")
    storage_dir = vault._storage.paths.database.parent
    storage_dir.mkdir(mode=0o750)
    storage_dir.chmod(0o750)
    with pytest.raises(IncompleteVault, match="permissions are too broad"):
        vault.store_secret("first", "fake")
    assert stat.S_IMODE(storage_dir.stat().st_mode) == 0o750
    assert not vault._storage.paths.key.exists()
    assert not vault._storage.paths.database.exists()
    storage_dir.chmod(0o700)
    vault.store("first.dev", "fake-user", "fake")
    for path in (vault._storage.paths.key, vault._storage.paths.database):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(vault._storage.paths.key.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(storage_dir.stat().st_mode) == 0o700

    key = vault._storage.paths.key
    key.chmod(0o644)
    with pytest.raises(IncompleteVault, match="chmod go-rwx"):
        vault.get("first.dev")
    with pytest.raises(IncompleteVault, match="chmod go-rwx"):
        vault.store("first.dev", "fake-user", "changed")
    assert stat.S_IMODE(key.stat().st_mode) == 0o644
    key.chmod(0o600)
    assert vault.get("first.dev").password == "fake"
