"""Give example tests a temporary vault populated with fake credentials."""

import pytest

from clave import Credential, Vault


@pytest.fixture(scope="session")
def vault(tmp_path_factory: pytest.TempPathFactory) -> Vault:
    demo_vault = Vault(tmp_path_factory.mktemp("clave-example"))
    demo_vault.store("db_user.dev", "demo-user", "demo-only-password")
    return demo_vault


@pytest.fixture(scope="session")
def db_credentials(vault: Vault) -> Credential:
    return vault.get("db_user.dev")
