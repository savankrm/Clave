"""Local automation example: populate your vault with store commands beforehand."""

import pytest

from clave import Vault
from clave.models import Credential


@pytest.fixture(scope="session")
def vault() -> Vault:
    return Vault()


@pytest.fixture(scope="session")
def db_credentials(vault: Vault) -> Credential:
    return vault.get("db_user.dev")
