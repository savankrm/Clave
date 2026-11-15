# Clave user guide

Clave stores developer credentials and tokens in an encrypted vault on your
computer. Use the terminal to manage entries and the Python API when local code
needs the actual values.

Clave supports Python 3.10 and newer on Windows, macOS, and Linux.

## 1. Install Clave

After it is published:

```console
python -m pip install clave
```

For review from this checkout:

```console
python -m pip install dist/clave-0.1.0-py3-none-any.whl
clave --help
```

If `clave` is not found, use `python -m clave`. Use the same Python interpreter
for installation and execution.

## 2. Store your first credential

No separate initialization is required. Your first successful store automatically
creates the random encryption key and database for your user account:

```console
clave store db_user.dev ExampleUser
```

Enter the password at the hidden `Password:` prompt. Clave reports that it created
the vault and credential. Future commands reuse that vault without an unlock prompt.

Installation itself does not create user files. Python package installers may run
in isolated build environments, as an administrator, or for a different user.
Creating the vault on the first store ensures it belongs to the person using Clave.

## 3. Name entries

Credentials always use `topic.environment`. Secrets can be global with `topic`, or
environment-specific with `topic.environment`:

```text
db_user.dev
db_user.qa
api_token
api_token.staging
```

Credential IDs have exactly one dot. Secret IDs have zero or one dot. Each part
starts with an ASCII letter and contains at most 64 ASCII letters, digits,
underscores, or hyphens. Names are case-sensitive. Environments are created
automatically; there is no setup command.

## 4. Store credentials and standalone secrets

A credential contains a username and password:

```console
clave store db_user.dev ExampleUser
```

A global standalone secret contains one token, key, or value:

```console
clave secret store api_token
```

Add an environment when the secret differs by environment:

```console
clave secret store api_token.qa
```

Hidden prompts are preferred. Positional values work but may be visible in shell
history or process listings:

```console
clave store db_user.dev ExampleUser example-only
clave secret store api_token example-token-only
clave secret store api_token.qa qa-example-token-only
```

Clave warns on stderr when a value is positional and never repeats that value in
its own output. Blank usernames, passwords, and secret values are rejected.

## 5. Replace an existing value

Use the same store command again. There are no update commands.

Replace the complete credential, including its username:

```console
clave store db_user.dev NewUsername
```

Replace a standalone secret:

```console
clave secret store api_token
clave secret store api_token.qa
```

Clave reports `created` for a new ID and `replaced` for an existing ID. A credential
cannot replace an environment-scoped secret with the same ID, or vice versa.
The separate credential and `secret` commands are deliberate: a token and password
can look identical, so Clave does not guess entry type from arguments or values.

## 6. Inspect entries safely

```console
clave get db_user.dev
clave secret get api_token
clave secret get api_token.qa
clave list
clave list --env dev
```

Terminal reads display metadata only. Credential inspection shows ID, environment,
type, and username. Secret inspection shows ID, environment, and type. Lists show
IDs and types. Global secret metadata says `scope: global`; scoped secret metadata
shows its environment. Passwords and secret values are never displayed by the CLI.
An unfiltered list includes both secret scopes. `list --env dev` includes only
credentials and scoped secrets for `dev`, excluding global secrets.

## 7. Retrieve values in Python

```python
from clave import Vault

vault = Vault()

credential = vault.get("db_user.dev")
username = credential.username
password = credential.password
global_token = vault.get_secret("api_token")
qa_token = vault.get_secret("api_token.qa")

# Pass these values directly to local code. Do not print or log them.
```

The explicit API values are plaintext so local automation can use them. Credential
objects redact their fields when printed, but `.password` returns the actual value.
`get_secret()` returns an ordinary plaintext string.

Python writes also create the vault automatically on the first call and replace
same-type entries on later calls:

```python
from clave import Vault

vault = Vault()

result = vault.store("example.dev", "ExampleUser", "example-only")
assert result.action in {"created", "replaced"}

vault.store_secret("example_token", "global-example-token-only")
vault.store_secret("example_token.qa", "qa-example-token-only")

# Store again to replace the full value.
vault.store("example.dev", "NewUser", "replacement-only")
vault.store_secret("example_token", "replacement-global-token-only")
vault.store_secret("example_token.qa", "replacement-qa-token-only")
```

Reads do not create an empty vault. If no entry has ever been stored, a read tells
you to store the first credential or secret.

## 8. Use Clave with pytest

Store the required credential locally, then add fixtures to your test project's
`conftest.py`:

```python
import pytest
from clave import Vault


@pytest.fixture(scope="session")
def vault():
    return Vault()


@pytest.fixture(scope="session")
def db_credentials(vault):
    return vault.get("db_user.dev")
```

There is no Clave pytest plugin. Keep credential fields out of test logs and failure
messages. V1 is for local automation and does not provide secure CI/CD key delivery.

## 9. Delete an entry

```console
clave delete db_user.dev
```

The CLI asks for confirmation and defaults to No:

```text
Delete db_user.dev? SQLite deletion is not forensic erasure. [y/N]:
```

Enter `y` or `Y` to delete. Enter `n`, `N`, or press Enter to cancel. For deliberate
local scripts, `clave delete db_user.dev --yes` bypasses confirmation. Python's
`vault.delete("db_user.dev")` does not prompt.

SQLite deletion is not secure forensic erasure. Storage remnants or snapshots may
still contain prior data.

## 10. Vault locations

| OS | Key | Database |
|---|---|---|
| Windows | `%LOCALAPPDATA%\clave\config\vault.key` | `%LOCALAPPDATA%\clave\data\vault.sqlite3` |
| macOS | `~/Library/Application Support/clave/config/vault.key` | `~/Library/Application Support/clave/data/vault.sqlite3` |
| Linux | `~/.config/clave/vault.key` | `~/.local/share/clave/vault.sqlite3` |

Linux follows XDG path settings when configured. Keep real vaults out of source
repositories and shared folders.

For a temporary or isolated vault:

```python
from tempfile import TemporaryDirectory
from clave import Vault

with TemporaryDirectory() as directory:
    vault = Vault(data_dir=directory)
    vault.store_secret("example", "fake-global-test-value")
    vault.store_secret("example.dev", "fake-dev-test-value")
    assert vault.get_secret("example") == "fake-global-test-value"
    assert vault.get_secret("example.dev") == "fake-dev-test-value"
```

The CLI equivalent is `clave --data-dir PATH store ...`. Repeat `--data-dir PATH`
for every command that should use that vault. Clave creates `config/vault.key` and
`data/vault.sqlite3` under the chosen root on its first successful store.

## 11. Troubleshooting

| Symptom | Resolution |
|---|---|
| `clave` is not recognized | Use `python -m clave` with the interpreter where Clave is installed. |
| Installation rejects your Python | Upgrade to Python 3.10 or newer. |
| Vault does not exist yet | Store the first credential or secret; no init command is needed. |
| Incomplete vault | Stop and check the selected root. Never regenerate a key for an existing database. |
| Entry does not exist | Check the exact case-sensitive topic and environment. |
| Entry has a different type | Use `store` for credentials and `secret store` for standalone values. |
| Interactive input unavailable | Run store in an interactive terminal or deliberately provide the value positionally. |
| `get` does not show a password | Expected: terminal reads show metadata; Python API reads return values. |
| Authentication or corruption error | Stop changing files and verify the selected root. V1 has no recovery tool. |

## 12. Security limits

- Database-only theft does not reveal encrypted record payloads without the key.
- Anyone with both files, or code running with your account's permissions, can decrypt records.
- IDs, entry types, timestamps, database structure, and Fernet creation times remain visible.
- Losing either file or corruption can permanently lose all records.
- V1 has no backup/restore, recovery, rotation, OS keychain, cloud fallback, or secure CI secret delivery.

See [SECURITY.md](SECURITY.md) for the full threat model, [README.md](README.md) for
the project overview, and [PUBLISHING.md](PUBLISHING.md) for owner release steps.
