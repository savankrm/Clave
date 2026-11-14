# Clave 0.1.0 release status

Updated: 2026-11-14

| Day | State | Exit condition |
|---|---|---|
| Day 1 - repository foundation | Complete | Commit `aced2b2` and status update pushed |
| Day 2 - encrypted vault core | Ready | Core commit pushed; API tests pass |
| Day 3 - CLI and user workflow | Ready | CLI commit pushed; CLI tests pass |
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
