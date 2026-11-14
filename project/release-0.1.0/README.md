# Clave 0.1.0 - five-day Git and release project

This project moves the completed Clave source into GitHub through small,
reviewable pushes and finishes with a release-ready `0.1.0` package.

## Project settings

- Working branch: `release/clave-0.1.0`
- Base branch after integration: `main`
- Package version: `0.1.0`
- Supported Python: 3.10 and newer
- Start date: 2026-11-14
- Target completion: 2026-11-18
- Publication: owner approval required after the Day 5 gate

The GitHub repository URL must be added before the first push. Build artifacts,
tool environments, vault databases, and keys remain untracked.

## How the incremental history is organized

Each day has one theme and one or more focused commits. Do not mix unrelated files
into a commit. Before every push, inspect `git diff --check`, review the staged file
list, and ensure the day's verification passes.

| Day | Date | Deliverable | Planned commit |
|---|---|---|---|
| 1 | 2026-11-14 | Repository, packaging, license, overview, project plan | `chore: establish Clave 0.1.0 project` |
| 2 | 2026-11-15 | Identifiers, models, encryption, paths, storage, Vault API | `feat: add encrypted local vault core` |
| 3 | 2026-11-16 | CLI, global/scoped secrets, examples, user guide | `feat: add safe credential and secret CLI` |
| 4 | 2026-11-17 | Tests, security review, smoke checks, full CI matrix | `test: verify Clave security and compatibility` |
| 5 | 2026-11-18 | Release documentation, clean build, TestPyPI rehearsal | `docs: finalize Clave 0.1.0 release` |

## Day 1 - repository foundation

Commit only the repository and product foundation:

```text
.gitignore
.gitattributes
LICENSE
pyproject.toml
README.md
CLAVE_CODING_AGENT_BRIEF.md
project/release-0.1.0/README.md
project/release-0.1.0/STATUS.md
```

Owner inputs required on Day 1:

1. GitHub repository URL.
2. Git commit email.
3. Repository visibility: public or private.
4. Confirmation of the public author name and optional public package email.

Before committing, add `[project.urls]` to `pyproject.toml` and replace relative
README documentation links with full GitHub URLs.

Verification:

```powershell
python -c "from pathlib import Path; import tomllib; tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8')); print('pyproject.toml: OK')"
git diff --cached --check
```

Commit and push:

```powershell
git add .gitattributes .gitignore LICENSE pyproject.toml README.md CLAVE_CODING_AGENT_BRIEF.md project/release-0.1.0
git diff --cached --check
git commit -m "chore: establish Clave 0.1.0 project"
git push -u origin release/clave-0.1.0
```

## Day 2 - encrypted vault core

Commit the core package as one auditable security slice:

```text
src/clave/__init__.py
src/clave/config.py
src/clave/crypto.py
src/clave/exceptions.py
src/clave/identifiers.py
src/clave/models.py
src/clave/py.typed
src/clave/storage.py
src/clave/vault.py
```

Verification:

```powershell
python -m ruff check src/clave
python -m mypy --python-version 3.10 src/clave
python -m pytest tests/test_vault.py
```

Commit and push:

```powershell
git add src/clave
git diff --cached --check
git commit -m "feat: add encrypted local vault core"
git push
```

## Day 3 - CLI and user workflow

Commit the command-line surface and user-facing examples:

```text
src/clave/__main__.py
src/clave/cli.py
examples/conftest.py
USER_GUIDE.md
```

Confirm these flows:

- First store creates the vault automatically.
- Credential IDs require `topic.environment`.
- Secrets accept global `topic` and scoped `topic.environment`.
- Repeating store replaces the complete same-type value.
- CLI reads never display secret values.
- Delete asks `[y/N]` and defaults to No.

Verification:

```powershell
python -m ruff check src/clave tests
python -m pytest tests/test_cli.py
```

Commit and push:

```powershell
git add src/clave/__main__.py src/clave/cli.py examples USER_GUIDE.md
git diff --cached --check
git commit -m "feat: add safe credential and secret CLI"
git push
```

## Day 4 - verification and CI

Commit automated checks and security evidence:

```text
tests/test_vault.py
tests/test_cli.py
scripts/smoke_wheel.py
SECURITY.md
IMPLEMENTATION_REPORT.md
.github/workflows/ci.yml
```

Run locally:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy --python-version 3.10 src/clave
python -m pytest
python -m build --no-isolation
```

After pushing, wait for every GitHub Actions job covering Python 3.10-3.15 on
Windows, macOS, and Linux. Correct any failure before Day 5.

Commit and push:

```powershell
git add tests scripts SECURITY.md IMPLEMENTATION_REPORT.md .github/workflows/ci.yml
git diff --cached --check
git commit -m "test: verify Clave security and compatibility"
git push
```

## Day 5 - release rehearsal

Commit the publishing guide after the CI matrix is green:

```text
PUBLISHING.md
```

Build the release into a new directory, validate it, install it into a fresh
environment, and publish it to TestPyPI by following `PUBLISHING.md`.

Commit and push:

```powershell
git add PUBLISHING.md project/release-0.1.0/STATUS.md
git diff --cached --check
git commit -m "docs: finalize Clave 0.1.0 release"
git push
```

Then open a pull request from `release/clave-0.1.0` to `main`. Merge only when:

- All checks are green.
- TestPyPI installation succeeds.
- Package metadata and documentation links are public and correct.
- The owner approves the license, version, and security statements.

Publishing to real PyPI and creating a Git tag remain separate owner-approved
actions after the merge.

## Rules for all five days

- Never commit a vault key, SQLite vault, API token, password, or real credential.
- Never force-push the shared release branch.
- Do not commit `dist`, `release-dist`, `.quality`, `.smoke`, caches, or coverage data.
- Do not rewrite a pushed commit; add a corrective commit.
- Use fake values and temporary vaults for every test.
- Check the exact staged file list before each commit with `git status --short`.
