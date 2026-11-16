# Clave 0.1.0 release status

Updated: 2026-11-17

| Day | State | Exit condition |
|---|---|---|
| Day 1 - repository foundation | Complete | Commit `aced2b2` and status update pushed |
| Day 2 - encrypted vault core | Complete | Core commit `e62fcf8` and status update pushed |
| Day 3 - CLI and user workflow | Complete | CLI commit `b663f84` and status update pushed |
| Day 4 - verification and CI | Complete with owner waiver | Local checks passed, 15 CI jobs passed, 3 macOS jobs waived |
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

## Day 4 checkpoint

- Committed and pushed the six named Day 4 files in `23f1595`.
- With owner approval, corrected Windows-only stat attribute access in
  `src/clave/config.py` in `b27dd70` for POSIX strict type checking.
- Corrected macOS temporary-directory symlink handling in the wheel smoke script
  in `a6e0268`.
- Using installed system Python 3.15.2, Ruff lint, formatting, strict mypy targeting
  Python 3.10, the complete pytest suite, package build, strict Twine validation
  and installed-wheel native smoke testing passed.
- Strict mypy also passed with a Linux platform target. Local checking used the
  existing pure-Python mypy 1.18.2 due to Windows Application Control restrictions.
- Local pytest reported 45 passed, one expected Windows POSIX-permission skip,
  and 99% total coverage. Crypto, identifiers, storage, Vault and CLI reached 100%.
- Staged patch review for secrets and `git diff --cached --check` passed.
- CI run https://github.com/savankrm/Clave/actions/runs/43942103512 recorded
  15 successful jobs for `a6e0268` at the completion checkpoint.
- All Python 3.10–3.15 jobs passed on Windows and Linux. macOS Python 3.10,
  3.13 and 3.15 passed. Remote Windows 3.10 reported 45 passed and one expected
  skip. Remote macOS 3.10 reported 46 passed. Both reported 99% coverage and
  successful installed-wheel smoke checks.
- On 2026-11-17, the owner explicitly waived the remaining macOS Python 3.11,
  3.12 and 3.14 jobs because runner allocation was taking too long and accepted
  Day 4 as complete. These three combinations have no verified passing result
  in this checkpoint. Their cancellation was left to the owner.
- Day 4 completion uses this owner waiver of the original all-18-jobs-green gate.
