# CLAVE — V1 Coding-Agent Build Specification

## Owner-approved adjustments — 2026-11-14

These decisions supersede conflicting text later in this original build brief:

1. Support Python 3.10 and every newer Python version. Package metadata uses
   `requires-python = ">=3.10"`; CI tests Python 3.10 through the latest version
   available to the project.
2. There is no `clave init` command or public `Vault.init()` method. Package
   installation does not create user files. The first successful `store` or
   `store_secret` call creates the key and database automatically. Reads never
   create an empty vault. Existing or partial vault safety rules still apply.
3. There are no update commands or update API methods. Repeating `store` for an
   existing credential replaces the full username/password payload. Repeating
   `secret store` replaces the full secret value. Cross-type replacement still fails.
4. Interactive CLI deletion explicitly prompts Y/N and defaults to No. `--yes`
   remains the deliberate noninteractive bypass.
5. Credentials require `topic.environment`. Secrets support both a global `topic`
   identifier and an environment-specific `topic.environment` identifier. Keep the
   credential and secret CLI commands explicit; do not infer entry type from values.

**Role:** You are the lead Python engineer and security-minded maintainer. Implement **Clave V1 end-to-end** in the current repository. This document is the complete source of product requirements; no chat history, screenshots, or other codebases are required. **V2 is design context only: do not implement it.**

## 0. Execution contract (read first)

1. Inspect the repository and preserve relevant existing Clave work; otherwise scaffold from scratch. Do not assume any prior package, migrate legacy data, or invent integrations.
2. Implement **all V1 requirements** below, including CLI, public API, encrypted persistence, tests, docs, and packaging. Work in small verifiable increments; run tests after each major layer. Do not stop after scaffolding or deliver only a plan.
3. Use the exact public contracts below. For unspecified minor details, pick the simplest secure and testable behavior and document it; do not ask routine questions or silently widen scope. If a genuine security blocker prevents safe implementation, explain it explicitly rather than pretending completion.
4. Keep implementation modular, typed, and dependency-light. No homemade cryptographic algorithms, plaintext secret persistence, hardcoded keys, unnecessary abstraction, or production secrets in examples/tests.
5. **Finish gate:** run lint, format check, type check, tests, build, and a clean-wheel smoke test; fix failures where possible. Report commands actually run and outcomes, remaining risks, and exact files changed. Never claim checks passed if they were not run. Do **not** push, publish to PyPI, or tag releases without owner authorization.

## 1. Product definition and fixed decisions

**Clave** (`pip install clave`, executable `clave`, Python import `from clave import Vault`) is a **single-user, local-first encrypted credential manager** for developers and **local Python/pytest automation** on Python **3.10 and newer**, Windows, macOS, and Linux.

- Credentials are addressed as **`topic.environment`** (e.g. `db_user.dev`). Secrets may use global **`topic`** (e.g. `api_token`) or scoped **`topic.environment`** (e.g. `api_token.qa`). Any valid environment is created implicitly on first store; no profile setup command.
- V1 stores two entry types: **credential** (`username` + `password`) and **secret** (standalone token/key/value).
- Data source is **only the local Clave vault**. No environment-variable or cloud credential fallback.
- **No unlock, master passphrase, Argon2id, or interactive prompt for reading/decrypting**: Python API and metadata-only CLI reads work automatically using a random key saved locally at initialization. CLI prompts for omitted values and deletion confirmation, **never** for vault unlocking.
- Storing an existing ID of the **same entry type overwrites automatically and atomically**, returning **created** or **replaced**; cross-type collisions fail without changing data.
- **CLI never displays a stored password, token, key, or generic secret**, including through `get`, flags, JSON, logs, or exception messages. Python API intentionally returns decrypted values for use in local test code.
- V1 is local-only and **not a supported secure CI/CD distribution/unlock solution**. Do not implement CI secret injection, remote vaults, or keychain integration. Since local-key reads are noninteractive, **do not artificially require a TTY to retrieve through the Python API**; noninteractive execution may technically work if vault files are accessible, but is outside the supported CI threat model.
- Backup/restore, key rotation, OS keychain, and managed key migration are **V2**, not V1. Document the recovery limitations in V1.

## 2. Exact CLI behavior

Use **Typer**. Console script: `clave`. Password/secret prompts must **hide input**. Passwords supplied as positional arguments are allowed by explicit product decision, but must trigger a conspicuous **stderr warning** (and must never appear in application logs or error output).

```console
clave store db_user.dev Username          # first store creates vault; hidden Password prompt
clave store db_user.dev Username 1234567  # allowed; WARN to stderr about shell history/process exposure
clave get db_user.dev                     # metadata only: id, environment, type, username; NO password
clave list                                # id and type, no secret values
clave list --env dev                      # exact environment filter
clave store db_user.dev NewU              # existing credential; replace full username/password
clave delete db_user.dev                  # confirmation before deletion; supports either entry type
clave secret store api_token.qa           # hidden prompt for value
clave secret store api_token              # global secret; hidden prompt for value
clave secret store api_token.qa TOKEN     # allowed; same stderr warning
clave secret get api_token.qa             # metadata only; NO value
clave secret store api_token.qa           # existing secret; hidden prompt replaces value
clave --help
```

**Output/edge rules:**
- The first successful store initializes a missing vault. If only key or only database exists, fail with a helpful **incomplete-vault** error; never silently replace/regenerate a key for an existing database. Explain that losing either file makes records unrecoverable in V1.
- After `store` print `Credential created: db_user.dev` or `Credential replaced: db_user.dev` (analogous `Secret ...`). Never print supplied values. Replacing a credential replaces both username and password.
- Hidden prompt only if no positional secret was supplied; reject blank values. If a secret is omitted and no interactive input is available, fail cleanly without hanging. Do not prompt to unlock for `get`, `list`, or Python reads.
- `get` means **inspect metadata**, not plaintext retrieval. Do **not** add `--show-password`, copy-to-clipboard, or plaintext CLI output in V1.
- `delete` must require an interactive confirmation by default; an explicit `--yes` may bypass confirmation for deliberate local scripting. Note SQLite deletion is **not secure forensic erasure**.
- Print friendly errors to stderr with appropriate nonzero exit codes; no raw tracebacks or secret-containing echoes for expected failures. Ensure CLI help matches behavior.

### Identifier contract

Credential IDs have **exactly one dot**. Secret IDs have zero dots for a global secret or exactly one dot for an environment-specific secret. Each component matches `^[A-Za-z][A-Za-z0-9_-]*$` and has at most **64** characters. Identifiers are **case-sensitive**, not normalized. Reject empty segments, extra dots, whitespace, Unicode outside the rule, and path separators. A unique `(topic, environment)` is shared across both entry types; global secrets use an internal empty environment. Profiles are logical filters, not a separate mandatory profile table.

## 3. Python API contract

```python
from clave import Vault

vault = Vault()  # OS-appropriate local paths; no passphrase or unlock call
result = vault.store("db_user.dev", username="Username", password="example-only")
assert result.action in {"created", "replaced"}
cred = vault.get("db_user.dev")
user, password = cred.username, cred.password
vault.store_secret("api_token", "global-example-token")
global_token = vault.get_secret("api_token")
vault.store_secret("api_token.qa", "qa-example-token")
qa_token = vault.get_secret("api_token.qa")
entries = vault.list(env="dev")
vault.store("db_user.dev", username="NewU", password="new-example")
vault.store_secret("api_token", "new-global-example-token")
vault.store_secret("api_token.qa", "new-qa-example-token")
vault.delete("db_user.dev")
```

- `Vault(data_dir=...)` must put **both database and key** under that isolated root (in separate subdirectories/files), never touching real user data. Default paths come from `platformdirs`; use separate config/data directories in production.
- `Vault()` / `Vault.get()` never ask for a passphrase. If the vault does not exist, reads raise a clear typed error; the first store initializes it automatically. Missing or partial key/database states fail closed.
- `get(id) -> Credential`, `get_secret(id) -> str`; wrong type raises `EntryTypeMismatch`; missing entry raises `EntryNotFound`. Plain values must never be redacted **in the explicit API return itself** or automation cannot use them.
- `store`/`store_secret` return a nonsecret result with `action: Literal["created", "replaced"]`. Repeating either operation replaces the complete same-type payload. `list(env=None)` returns metadata-only entries. `delete(id)` handles either type.
- Use typed immutable return models with **redacted `repr`/`str`** for credential objects; avoid accidentally leaking passwords via printing objects, exceptions, logs, or debugging. Clarify in docs that callers must also avoid logging returned plaintext strings.
- Pytest integration is **direct API + example session-scoped fixtures** only, not a Clave pytest plugin. A sample to include in the README (configured secrets must be present on the local machine):

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

Never use actual developer credentials in Clave’s own automated tests; use temporary vaults and fake values.

## 4. Security model (implement precisely)

**Accepted trade-off:** Encryption protects against an attacker who gets **only the SQLite database**. A person or malware with access to **both the key file and database**, or code running with the developer's permissions, can decrypt the secrets. **Separate files are not a separate trust boundary.** V1 is not intended to withstand full local-account compromise.

1. On the first successful store, generate a unique random **Fernet key** using `cryptography.fernet.Fernet.generate_key()`; never derive it from hostname, username, constant, or password. Save to a key file separately from SQLite. Do not store the key inside the database, source tree, repo, environment variable, or CLI arguments.
2. Encrypt authenticated, versioned JSON payloads with Fernet. Credential payload includes **username and password**; secret payload includes its value. Only necessary metadata (`topic`, `environment`, `type`, timestamps, schema version) may be plaintext in SQLite. Document that identifiers/timestamps remain visible and Fernet tokens expose a creation timestamp.
3. Create app directories and files with restrictive permissions: **POSIX dirs `0700`, key/db files `0600`** where supported; on Windows rely on appropriately restricted user-profile ACLs and document that POSIX chmod is not a Windows security guarantee. Do not use world-readable defaults. Refuse suspicious symlink paths for sensitive files where practical; never put files in the project tree by default.
4. Create the key with **exclusive creation**; avoid truncating existing key files. Handle interrupted/partial initialization explicitly; do not regenerate a missing or invalid key if a database exists. Verify a stored encrypted sentinel/key-check at open time so wrong-key and corruption failures are clear. Never automatically create an empty vault on `get`.
5. Use SQLite transactions and parameterized queries. Ensure same-type overwrite is atomic and preserves the previous record on encryption/database/write failure; under concurrency, do not silently cross-type overwrite. Set reasonable busy timeout and test competing reads/writes. Preserve `created_at`; change `updated_at` on replacement.
6. Decryption failures must be clean and nonrevealing; do not fall back to plaintext. Never log secret arguments, encryption keys, full `argv`, SQL payloads, or plaintext. Print warning on stderr when a secret is passed positionally—even though Clave cannot undo shell-history/process exposure that occurred **before it started**.
7. Do not promise secure deletion, protection from malware/compromised sessions, key recovery, or backup. **Losing the key file, losing the database, or corruption can cause irreversible data loss** in V1; prominently disclose this during initialization and in README/SECURITY.md. Recovery is accepted **low-priority risk**; do not expand V1 scope to build backup/rotation.

## 5. Data format, layering, and dependencies

**Only record payloads are encrypted; SQLite metadata and database structure are not encrypted.**

**SQLite schema (minimum):** `vault_meta(schema_version, key_provider, encrypted_key_check, created_at)` and `entries(topic, environment, entry_type, encrypted_payload, created_at, updated_at, PRIMARY KEY(topic, environment))`. Values are illustrative; choose a sensible schema with version checks. Encrypt JSON payloads like `{"v":1,"kind":"credential","username":"...","password":"..."}` or `{"v":1,"kind":"secret","value":"..."}`. Never use pickle. Fail gracefully on an unsupported future schema. Design migration seams; **do not implement migrations beyond V1**.

**Suggested modules:** `cli.py`, `vault.py` (facade), `crypto.py`, `storage.py`, `identifiers.py`, `models.py`, `config.py`, `exceptions.py`, plus `__init__.py`, `__main__.py`, and `py.typed`. Keep OS paths, encryption, SQL, and presentation separate. Prefer standard library for small tasks.

| Function | Choice |
|---|---|
| Runtime | Python 3.10 and newer |
| CLI | `typer` |
| Encryption | `cryptography` / Fernet |
| Database | built-in `sqlite3` |
| Cross-platform paths | `platformdirs` |
| Hidden prompt | `getpass` or Typer password prompt |
| Packaging | `pyproject.toml`, `hatchling`, `python -m build` |
| Tests / quality | `pytest`, `pytest-cov`, `ruff`, `mypy`, `pip-audit` (optional network-dependent audit) |
| CI | GitHub Actions to test Clave itself with **temporary fake vaults**, not real production credentials |

Do **not** add Argon2id, `keyring`, cloud SDKs, or backup/rotation dependencies to **V1**. Define a narrow internal key-provider interface or replaceable seam (`LocalFileKeyProvider`) to ease V2 adoption; do not build a provider registry or plugin system now.

## 6. Build sequence — agent must execute, not merely describe

1. **Scaffold:** `src/clave/`, `tests/`, `examples/`, CLI entry point, pyproject (set `requires-python = ">=3.10"` and supported-version classifiers), README, SECURITY.md, license file (MIT default for owner review), workflows. Install dev dependencies in an isolated environment.
2. **Contracts:** exceptions, identifiers, models, typed API signatures, OS-safe config/paths; test validation first.
3. **Crypto/automatic initialization:** first-store key generation, exclusive secure key creation, encrypted key check, Fernet encrypt/decrypt, missing/invalid-key behavior; test tampering and partial initialization.
4. **Storage:** SQLite schema, concurrency, typed CRUD and atomic same-type upsert; tests for rollback/collisions.
5. **Vault:** implement credential + generic-secret API, metadata listings/filter, store-based replacement and delete; test with temporary directories.
6. **CLI:** Typer commands, prompts, warnings, created/replaced output, metadata-only retrieval, confirmations, clean error messages; CLI tests with `CliRunner`/subprocess.
7. **Documentation:** install/automatic-first-store/get/list/delete, security trade-offs, pytest fixture for local test automation, Windows/macOS/Linux paths, V1 limitations, V2 roadmap.
8. **Verification:** run all checks in §7; fix defects until acceptance passes. Build/install wheel in a fresh environment and smoke-test CLI and Python import. Summarize actual results; do not publish.

## 7. Acceptance criteria / release gate

All items below must have automated tests where feasible:

- Wheel installs, `clave --help` works, `from clave import Vault` succeeds on supported Python versions.
- First store generates a random key file separate from an encrypted SQLite vault; existing/partial vaults cannot be accidentally reset; no unlock/password prompts on subsequent Python or CLI reads.
- CLI missing-password path prompts with no echo. Positional password/token path succeeds with a **stderr warning**, no secret value in Clave-generated stdout/stderr/logs. Blank secret fails.
- `db_user.dev` and `db_user.qa` are independent; arbitrary valid environments work; global and scoped secrets work; `list --env dev` includes only entries scoped to `dev` and excludes global secrets; invalid names fail.
- `get`/`secret get`/`list` never emit secret data, while Python `get` and `get_secret` return correct plaintext. Credential object representation does not expose password.
- Duplicate same-type store yields `replaced` and preserves valid prior record on failed overwrite; cross-type collision fails; delete confirms Y/N; database transactions and concurrency do not corrupt records.
- Invalid key, missing key, malformed ciphertext, tampering, and newer unknown schema fail safely without silently creating/reinitializing data.
- DB payload never includes plaintext username/password/token; no plaintext secrets in tracked files, exceptions, or test snapshots. Tests use only fake values and temporary paths.
- README contains copyable CLI/Python/pytest examples, `get` metadata-only caveat, local key-file threat model, and low-priority recovery risk. SECURITY.md specifies what Clave does **not** defend against.
- Run and report: `ruff check .`, `ruff format --check .`, `mypy src/clave`, `pytest` with coverage (aim **≥90% for security-critical code**), `python -m build`, fresh-wheel smoke test; run `pip-audit` if available. CI runs tests with Python 3.10 through the latest declared version on Windows, macOS, and Linux.

## 8. V2 design scope — **future only, do not code now**

Keep V1's identifiers, public API, schema version, encrypted payload version and small key-provider seam upgradeable for:

| V2 capability | Use case / intended design | Trade-off / constraint |
|---|---|---|
| **OS keychain (`keyring`)** | Protect Clave's random encryption key via Windows Credential Manager, macOS Keychain, or Linux Secret Service, instead of ordinary key-file storage. Preserve prompt-free API reads **when OS policy permits**. | Better protection from simple file theft, but backend availability and prompts vary; some Linux/headless setups lack a usable keychain; same-user malware may still retrieve unlocked secrets. Migration must verify the new key location before removing old file; no silent insecure fallback. |
| **Encrypted backup / restore** | Portable authenticated export with a user-chosen backup passphrase and a modern KDF (e.g. Argon2id), verified import and collision policy. | More complexity and backup-passphrase management; never export raw local key as a plaintext artifact. |
| **Key rotation / recovery tools** | Safely re-encrypt vault entries and recover from interrupted rotation. | Requires transactional staging, integrity checks, rollback, and explicit recovery procedures. No guaranteed recovery after all decryption keys are lost. |
| **Unattended CI support** | Opt-in key delivery or a secrets provider for headless automation; define a CI-specific threat model and precedence. | Do not silently read keys or secrets from environment variables in V1; CI use must avoid leaking credentials in logs. |
| **Cloud/provider resolution** | Optional environment/cloud secret managers and explicit, documented resolution ordering. | Added dependencies, auth, and surprising-fallback risks. |
| **Pytest plugin / advanced profiles** | First-party fixtures, environment selection, profile management, batch operations. | Maintain stable direct `Vault` API and `topic.environment` meaning. |
| **Other language clients** | Optional Node/TypeScript package after formally specifying shared encrypted format and interop tests. | Python Fernet cannot be assumed to match Node AES-GCM or any alternate format. |

**Final agent report format:** `Implemented` (files/features); `Verification` (exact command + pass/fail/not run); `Security limits`; `Pending owner decisions` (only real blockers). **Stop at finished V1 source and verified build; no release action.**
