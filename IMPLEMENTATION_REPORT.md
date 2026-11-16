# Clave V1 implementation evidence

## Day 4 scope

Days 1–3 are complete in the pushed history, with foundation commit `aced2b2`,
core commit `e62fcf8`, CLI commit `b663f84` and status checkpoint `07cab7e`.
Day 4 adds the two test modules, wheel smoke script, security documentation,
implementation evidence and GitHub checking workflow.

## Security and compatibility evidence

Vault tests exercise identifier boundaries, global/scoped secrets, type collisions,
replacement and timestamps, metadata filters, redacted representations, invalid
first stores, incomplete initialization, invalid/wrong keys, independent random
keys, exclusive creation, encrypted payloads, tampering, unsupported schemas,
authenticated malformed JSON, corrupt databases, failed encryption and SQL rollback,
concurrent reads/writes, cross-type races, concurrent initialization across Vault
instances, isolated paths, symlinks and POSIX permissions.

CLI tests exercise metadata-only reads, hidden prompts, positional-value warnings,
replacement, global/scoped secrets, environment filters, confirmation, unavailable
interactive input, removed commands, parser redaction and help.
All tests use fake values and temporary vaults.

The wheel smoke script checks the import origin, native launcher, automatic store
initialization, API plaintext round trips, metadata-only reads, warnings, replacement,
filtering, type errors, invalid IDs, blank values, confirmation and deletion.
Both output streams are checked for fake secret disclosure.

## Local checks on 2026-11-17

All Python commands use the installed system Python 3.15.2 at
`C:\Users\Savan\AppData\Local\Python\pythoncore-3.15-64\python.exe`.
Tool dependencies are in ignored project-local directories.

| Check | Result |
|---|---|
| Ruff lint | Passed |
| Ruff formatting check | Passed, 23 files |
| Strict mypy targeting Python 3.10 | Passed, 10 source files |
| Complete pytest suite with coverage | 45 passed, 1 expected skip, 99% coverage |
| sdist and wheel build using `build --no-isolation` | Passed |
| Twine `check --strict dist/*` | Passed for both artifacts |

Crypto, identifiers, storage, Vault and CLI each reached 100% statement coverage.
Config reached 97%. The launcher statements and one config branch remain uncovered.
Windows skips the POSIX permission assertion because modes cannot verify Windows
ACLs. Symlink rejection passed here, while hosts lacking symlink privileges may
explicitly skip that test. Pytest emitted a pre-existing cache-directory warning.

Strict mypy uses the existing pure-Python 1.18.2 checker in `.typecheck-legacy`
because Windows Application Control blocks native checker modules on this host.
CI uses normally resolved mypy with explicit strict mode and Python 3.10 target.

Fresh wheel installation uses `.smoke/day4` with only that directory on PYTHONPATH,
then runs `scripts/smoke_wheel.py .smoke/day4 .smoke/day4/bin/clave.exe`.
The script asserts the imported package belongs to the installed target.

## Remote CI gate

The workflow runs all 18 combinations of Python 3.10–3.15 and Ubuntu, Windows,
and macOS. Every job runs lint, formatting, strict Python-3.10-targeted mypy,
pytest with coverage, package build, strict Twine validation, and fresh-venv
installed-wheel smoke checks. Workflow permissions are read-only.
Remote results are recorded in `project/release-0.1.0/STATUS.md` after all jobs pass.

## Security limits

`SECURITY.md` documents database-only payload protection, visible metadata and
Fernet timestamps, same-user compromise, theft of both files, Windows ACLs,
filesystem races, plaintext API handling, forensic-deletion limitations,
irreversible loss, and the V1 recovery and CI distribution limitations.

Installed-wheel native smoke result was PASS on 2026-11-17.
