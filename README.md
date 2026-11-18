# Clave

**Keep secrets out of your Python code.**

Clave is a local encrypted vault for passwords and API tokens used in Python
development and test automation. It supports Python 3.10 and newer on Windows,
macOS, and Linux.

**Release status.** Clave is a developer beta.

## Quick start

For a packaged release, start with the
[TestPyPI and PyPI installation instructions](https://github.com/savankrm/Clave/blob/main/USER_GUIDE.md#1-install-clave).

To try Clave from source, run these commands in an active virtual environment.

```console
git clone https://github.com/savankrm/Clave.git
cd Clave
python -m pip install .
```

Save a test credential from the terminal.

```console
clave store db_user.dev ExampleUser
```

Enter a password at the prompt. Clave shows asterisks as you type. The first
successful store creates the vault automatically. Retrieve the credential from
Python code running under the same user account:

```python
from clave import Vault

credential = Vault().get("db_user.dev")
username, password = credential.username, credential.password
```

Pass the values directly to your application and keep them out of logs. To see
how a test can use a saved credential, run the
[pytest login example](https://github.com/savankrm/Clave/tree/main/examples).
The [quick start](https://github.com/savankrm/Clave/blob/main/QUICKSTART.md)
walks through saving and restoring a test credential.

## Manage entries

Run `clave` in a terminal to open the menu. You can also run each command directly:

```console
clave secret store api_token
clave secret store api_token.qa
clave get db_user.dev
clave secret get api_token
clave list
clave list --env dev
clave find github
clave delete db_user.dev
```

In the menu, choose **View entries** to search. For a manual login,
`clave copy db_user.dev` copies the saved password to the system clipboard.
Clipboard history and sync may retain it. See the
[clipboard instructions](https://github.com/savankrm/Clave/blob/main/USER_GUIDE.md#6-inspect-entries-safely)
for platform requirements.

Password and secret prompts hide input. Supplying a value positionally is allowed,
but Clave warns that shell history and process listings may expose it:

```console
clave store db_user.dev Username example-only
clave secret store api_token example-token
clave secret store api_token.qa qa-example-token
```

Run the store command again to replace an entry. Clave asks for confirmation in
an interactive terminal. Type `y` to replace it or press Enter to keep what you
saved. Use `--replace` to skip confirmation or to replace an entry in a script.

```console
clave store db_user.dev NewUsername
clave secret store api_token
```

Environment-scoped credentials and secrets share the same ID namespace. A
credential cannot replace a scoped secret with the same ID, or vice versa.
The explicit `store` and `secret store` commands make entry type intentional;
Clave does not guess from argument count or value shape.

Deletion asks for explicit Y/N confirmation and defaults to No:

```text
Delete db_user.dev? Copies may remain in storage or backups. [y/N]:
```

`clave delete db_user.dev --yes` bypasses confirmation for deliberate local
scripts.

## Identifiers

Credential IDs are always `topic.environment`, for example `db_user.dev`. Secret
IDs support both `topic` for a global secret and `topic.environment` for an
environment-specific secret, for example `api_token` and `api_token.qa`. Each
component starts with an ASCII letter and has at most 64 ASCII letters, digits,
underscores, or hyphens. IDs are case-sensitive. Environments are created
implicitly; there is no environment setup command.

## Terminal reads are metadata-only

`get`, `secret get`, and `list` never display passwords, tokens, keys, or generic
secret values. Credential inspection includes its username. Python API calls return
plaintext intentionally for local automation. An unfiltered list includes global
and scoped secrets. `list --env dev` includes credentials and scoped secrets for
`dev`, while global secrets are omitted from environment-filtered results.

```python
from clave import Vault

vault = Vault()

# The first write creates the vault automatically when it does not exist.
result = vault.store(
    "db_user.dev",
    username="Username",
    password="example-only",
)
assert result.action in {"created", "replaced"}

credential = vault.get("db_user.dev")
user, password = credential.username, credential.password

vault.store_secret("api_token", "global-example-token")
global_token = vault.get_secret("api_token")
vault.store_secret("api_token.qa", "qa-example-token")
qa_token = vault.get_secret("api_token.qa")
entries = vault.list(env="dev")

# Store again to replace the complete value.
vault.store("db_user.dev", username="NewU", password="new-example")
vault.store_secret("api_token", "new-global-example-token")
vault.store_secret("api_token.qa", "new-qa-example-token")
vault.delete("db_user.dev")
```

Credential objects are immutable and redact fields from `repr` and `str`. Accessing
`.password`, or calling `get_secret`, still returns plaintext. Callers must keep
those explicit values out of logs and failure messages.

Reads do not create an empty vault. Before the first store they raise
`VaultNotInitialized` with guidance to store an entry. An incomplete vault—only a
key or only a database—fails closed and is never silently repaired or regenerated.

## Pytest integration

Clave uses direct API fixtures rather than a pytest plugin. Store the credential on
the local machine before running the tests:

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

Clave's own tests use only temporary vaults and fake values.

## Vault locations

| OS | Key | Database |
|---|---|---|
| Windows | `%LOCALAPPDATA%\clave\config\vault.key` | `%LOCALAPPDATA%\clave\data\vault.sqlite3` |
| macOS | `~/Library/Application Support/clave/config/vault.key` | `~/Library/Application Support/clave/data/vault.sqlite3` |
| Linux | `~/.config/clave/vault.key` | `~/.local/share/clave/vault.sqlite3` |

Linux honors standard XDG path configuration. For isolated tests,
`Vault(data_dir=temporary_path)` and `clave --data-dir PATH ...` put both files
under that root in separate `config` and `data` directories.

## Security and recovery limits

Fernet encrypts authenticated, versioned JSON payloads, including usernames. IDs,
types, timestamps, database structure, and Fernet creation timestamps remain
visible. Encryption protects against theft of the database alone. Anyone with both
the key and database, or code running with the developer's permissions, can decrypt
records. Separate files are not a separate trust boundary.

Use `clave doctor` to check the local vault. Save a passphrase-protected backup
before you need it and test the restore into a separate location:

```console
clave backup clave-backup.clave
clave --data-dir recovered-vault restore clave-backup.clave
clave --data-dir recovered-vault doctor
```

Use `clave export` and `clave import` for the same encrypted archive workflow
when moving a vault. Run `clave rotate-key` to replace the encryption key in
place. Clave also rotates a due key when you use the vault after 15 days.

Keep the backup and passphrase in separate safe locations. Losing either vault
file may permanently lose records without a usable backup. See the
[recovery instructions](https://github.com/savankrm/Clave/blob/main/USER_GUIDE.md#11-check-and-recover-your-vault)
and [security model](https://github.com/savankrm/Clave/blob/main/SECURITY.md) for details.

## Development

```console
python -m pip install ".[dev]"
ruff check .
ruff format --check .
mypy src/clave
pytest
python -m build
```

Pull request CI runs the suite on Python 3.10 through 3.15 on Windows, macOS, and
Linux. A push checks installation and `clave --help` on all three platforms
using the latest stable Python 3. See
[USER_GUIDE.md](https://github.com/savankrm/Clave/blob/main/USER_GUIDE.md) for the
complete manual,
[PUBLISHING.md](https://github.com/savankrm/Clave/blob/main/PUBLISHING.md) for owner
release steps, and
[CHANGELOG.md](https://github.com/savankrm/Clave/blob/main/CHANGELOG.md)
for release notes and verification results.

Released under the [MIT license](https://github.com/savankrm/Clave/blob/main/LICENSE).
