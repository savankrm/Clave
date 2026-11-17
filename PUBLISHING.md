# Publishing Clave 0.1.0

## Release rehearsal status

The release branch is `release/clave-0.1.0` in `savankrm/Clave`.
Day 4 completed with an owner waiver for delayed macOS jobs. The final observed
Day 4 run had 16 successful jobs and two cancelled jobs. The historical waiver
covers macOS Python 3.11, 3.12 and 3.14, with 3.11 subsequently passing.
See [CHANGELOG.md](CHANGELOG.md) for release notes and verification results.

TestPyPI rehearsal must succeed before production approval. The repository is
public. Uploaded distributions and their included Python source are public too.
The package version is `0.1.0`, requiring Python 3.10 or newer.

A wheel is the installable package. A source archive contains the build sources.
TestPyPI is the practice package index. Production PyPI serves normal pip installs.
Trusted Publishing exchanges the GitHub workflow identity for a short-lived upload
credential automatically. Keep permanent PyPI tokens out of this workflow.

## 1. Configure accounts and publishers

Create separate PyPI and TestPyPI accounts, verify email, enable two-factor
authentication and save recovery codes securely. Sign in to each account's
Publishing page and register a pending GitHub publisher with these exact values.

| Field | TestPyPI | PyPI |
|---|---|---|
| Project name | `clave` | `clave` |
| Owner | `savankrm` | `savankrm` |
| Repository | `Clave` | `Clave` |
| Workflow filename | `release.yml` | `release.yml` |
| Environment name | `testpypi` | `pypi` |

Enter the filename `release.yml` in the publisher form. Its repository path is
`.github/workflows/release.yml`. Replace any earlier publisher for `ci.yml`.
A pending publisher creates the project on first successful publication and does
not reserve its name. Recheck availability immediately before the first upload.

Account pages are https://test.pypi.org/manage/account/publishing/ and
https://pypi.org/manage/account/publishing/.

## 2. Configure manual approval on GitHub

Open https://github.com/savankrm/Clave/settings/environments.
Create `testpypi` and `pypi`. Under deployment protection rules, enable Required
reviewers and add the owner or an authorized reviewer. For a sole owner who will
trigger and approve the rehearsal, leave Prevent self-review disabled. Disable
administrator bypass where available. Save each environment's protection rules.

Under Deployment branches and tags, choose Selected branches and tags. Allow
branch `release/clave-0.1.0` for `testpypi`, and branch `main` for `pypi`.
No environment secrets are required for PyPI authentication.

Creating an environment name in YAML does not configure required reviewers.
Confirm the rules in GitHub before pushing the release workflow. The publisher
jobs pause for environment approval only when these rules have been saved.

## 3. Validate the release locally

From PowerShell in `E:\Clave`, use the installed system interpreter.

```powershell
$taskPython = 'C:\Users\Savan\AppData\Local\Python\pythoncore-3.15-64\python.exe'
$env:PYTHONPATH = 'E:\Clave\.quality;E:\Clave\src'
& $taskPython -m ruff check .
& $taskPython -m ruff format --check .
& $taskPython -m pytest -ra -o cache_dir=.quality/pytest-cache
& $taskPython -m mypy --strict --python-version 3.10 src/clave
& $taskPython -m build --no-isolation --outdir release-dist/0.1.0-rehearsal
& $taskPython -m twine check --strict release-dist/0.1.0-rehearsal/*
```

Use a new output directory for each build. If Windows Application Control blocks
native mypy modules, prepend the existing `.typecheck-legacy` directory to
PYTHONPATH for that check.

Inspect both archives for expected modules, `py.typed`, metadata and MIT license.
Exclude local tool directories, caches, vaults and the untracked handoff. Use a
clean tracked checkout for distributable source archives. Record SHA256 hashes.
Review the package README, Python requirements, public author and repository URLs.
Documentation links to main become available after the release PR is merged.

## 4. Push and approve the TestPyPI rehearsal

The new workflow must be committed and pushed before GitHub can execute it.
Stage only `PUBLISHING.md` and `.github/workflows/release.yml`, review the staged
patch for secrets and run `git diff --cached --check`. Push the release branch.
The workflow runs on changes to either release file on that branch. This trigger
allows rehearsal before the workflow has been merged to the default branch.
GitHub requires a workflow_dispatch workflow to exist on the default branch before
it can be manually dispatched. Later rehearsals can use the manual testpypi input.

The workflow builds once on Ubuntu/Python 3.10, runs lint, formatting, strict mypy,
tests with coverage, build, Twine, archive checks and installed-wheel smoke testing.
It retains both distributions as the `clave-distributions` artifact for 30 days.
The build job has read-only contents access. Only upload jobs receive OIDC access.

Open the release rehearsal run in Actions. Review the source commit and artifact
hashes, then approve its `testpypi` deployment under Review deployments. This uploads
publicly to TestPyPI through Trusted Publishing. The `pypi` job is skipped for
release-branch pushes.

After upload, the workflow creates a clean virtual environment, installs runtime
dependencies from PyPI, downloads exactly `clave==0.1.0` from TestPyPI with
`--no-deps`, compares its wheel byte-for-byte with the retained artifact, installs
it and runs the native CLI/API smoke script. Avoid an extra-index-url combination
when validating which index supplied Clave.

If indexing has not completed, rerun the failed verification job after the package
appears. Rerunning upload may fail because version files already exist. Inspect
which files succeeded before retrying. Changed distribution contents require a
new version, including on TestPyPI. Do not silently skip existing uploads.

## 5. Verify installation manually if needed

Use a new ignored environment and clear source PYTHONPATH first.

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
& $taskPython -m venv .smoke/testpypi-0.1.0
$reviewPython = 'E:\Clave\.smoke\testpypi-0.1.0\Scripts\python.exe'
& $reviewPython -m pip install 'cryptography>=50.0.2' 'typer>=0.28,<1.0' 'platformdirs>=4'
& $reviewPython -m pip install --index-url https://test.pypi.org/simple/ --no-deps 'clave==0.1.0'
& $reviewPython scripts/smoke_wheel.py .smoke/testpypi-0.1.0 .smoke/testpypi-0.1.0/Scripts/clave.exe --legacy-0.1.0
```

Confirm version 0.1.0 and the README, license and links on the TestPyPI project
page. The smoke script uses temporary fake vaults and checks output for disclosure.

## 6. Record rehearsal and prepare review

Record the successful rehearsal run ID, source SHA, artifact hashes, TestPyPI URL,
clean installation result and remaining owner decisions. Update CHANGELOG.md in a
separate commit and push. Open a draft PR from `release/clave-0.1.0` to `main`.
The owner reviews the package information, Day 4 waiver, rehearsal evidence,
environment protections and release workflow before approving integration.

## 7. Production remains an owner-approved later action

After owner approval, merge the PR and perform the separately approved tagging
steps. Production publication uses a manual workflow dispatch on `main` with
destination `pypi` and the successful release-branch rehearsal run ID. Approve the
protected `pypi` deployment only after reviewing that run and its hashes.

The production job verifies that the selected release.yml run on the release branch
succeeded, including TestPyPI installation verification, and downloads its retained
artifact. It uploads the exact rehearsed distributions without rebuilding.
Keep the artifact within its 30-day retention period. If it expires, prepare and
review a new rehearsal before production publication.

## Troubleshooting

| Symptom | Check |
|---|---|
| Missing Run workflow button | workflow_dispatch must exist on the default branch |
| Approval prompt absent | Save required reviewers on the named GitHub environment |
| invalid-publisher / OIDC failure | Exact owner, repository, release.yml and environment on the correct index |
| Deployment rejected | Environment branch restrictions and approval permissions |
| File already exists | Inspect prior uploads and avoid reusing changed version files |
| pip cannot find 0.1.0 | Correct TestPyPI URL, upload result and indexing delay |

Official references are [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/),
[GitHub environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
and [manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
