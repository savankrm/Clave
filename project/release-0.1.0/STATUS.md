# Clave 0.1.0 release status

Updated: 2026-11-16

| Day | State | Exit condition |
|---|---|---|
| Day 1 - repository foundation | Complete | Commit `aced2b2` and status update pushed |
| Day 2 - encrypted vault core | Complete | Core commit `e62fcf8` and status update pushed |
| Day 3 - CLI and user workflow | Complete | CLI commit `b663f84` and status update pushed |
| Day 4 - verification and CI | Ready | All local and GitHub matrix checks green |
| Day 5 - release rehearsal | Ready | TestPyPI install passes; release PR approved |

## Current blockers

- GitHub repository visibility has not been recorded for this release project.
- TestPyPI and PyPI credentials are not needed until the Day 5 release gate.

## Local Day 1 checkpoint

- Initialized the Git repository.
- Created and selected `release/clave-0.1.0`.
- Based the release branch on the existing `origin/main` history.
- Configured `origin` as `https://github.com/savankrm/Clave.git`.
- Configured the repository-local Git author identity.
- Committed and pushed only the Day 1 repository-foundation files.
- Confirmed `git diff --cached --check` passes.
- Parsed `pyproject.toml` with the installed system Python successfully.
- Set the upstream branch to `origin/release/clave-0.1.0`.

## Existing local evidence

- 45 tests passed with 99% coverage; one POSIX-only permission test skipped on Windows.
- Ruff formatting and lint passed.
- Strict mypy check targeting Python 3.10 passed.
- Wheel/source build and strict Twine validation passed.
- Native installed-wheel smoke test passed.

Repeat the checks on each day's staged state and record remote CI results here.

## Local Day 2 checkpoint

- Reviewed initialization, key handling, encrypted payloads, transaction safety,
  type collisions, identifiers, path safety, and redacted return models.
- Ruff lint passed for `src/clave`.
- Ruff formatting check passed for all 10 source files.
- Strict mypy targeting Python 3.10 passed for all 10 source files.
- The first Vault test attempt was blocked by an inaccessible Windows pytest temp
  folder; retrying with an ignored repository-local temp directory succeeded.
- Vault suite result: 38 passed and one expected POSIX-permission skip on Windows.
- Security-critical core coverage: crypto, identifiers, storage, and Vault 100%;
  config 97%.
- Staged-file and secret-pattern checks passed for the nine Day 2 files.
- Committed and pushed `e62fcf8` to `origin/release/clave-0.1.0`.

## Local Day 3 checkpoint

- Reviewed hidden prompts, positional-value warnings, noninteractive failures,
  metadata-only reads, same-type replacement, and delete confirmation.
- Ruff lint passed for source, the CLI tests, and the example fixture.
- Ruff formatting check passed for all 12 reviewed Python files.
- CLI suite result: 7 passed with `cli.py` at 100% coverage and 93% overall
  coverage for the CLI-only run.
- `python -m clave --help` succeeded with the installed system Python.
- Staged-file, whitespace, and secret-pattern checks passed for the four Day 3
  paths.
- Committed and pushed `b663f84` to `origin/release/clave-0.1.0`.
