# Publishing Clave

Both package indexes use the manual **release rehearsal** workflow on protected
`main` in `savankrm/Clave`. The release version comes from `pyproject.toml`.
The current release candidate is `0.2.1`, which requires Python 3.10 or newer.

TestPyPI is the practice index. Both TestPyPI and production PyPI make uploaded
packages public. Trusted Publishing exchanges the GitHub workflow identity for a
short-lived upload credential.

## 1. Configure accounts and publishers

Sign in to each index with your verified account. Check the existing publisher
in the TestPyPI project settings. For the first production release, create a
pending publisher in your PyPI account settings.

| Field | TestPyPI | PyPI |
|---|---|---|
| Project name | `clave` | `clave` |
| Owner | `savankrm` | `savankrm` |
| Repository | `Clave` | `Clave` |
| Workflow filename | `release.yml` | `release.yml` |
| Environment name | `testpypi` | `pypi` |

Enter `release.yml` as the workflow filename. The repository path is
`.github/workflows/release.yml`. A pending publisher creates the project on
its first successful upload. Recheck the production project name before approval.

Account pages are https://test.pypi.org/manage/account/publishing/ and
https://pypi.org/manage/account/publishing/.

## 2. Configure manual approval on GitHub

Open https://github.com/savankrm/Clave/settings/environments.
Create `testpypi` and `pypi`. Under deployment protection rules, enable Required
reviewers and add the owner or an authorized reviewer. For a sole owner who will
trigger and approve the rehearsal, leave Prevent self-review disabled. Disable
administrator bypass where available. Save each environment's protection rules.

Under **Deployment branches and tags**, choose **Selected branches and tags**
and allow `main` in both environments.
No environment secrets are required for PyPI authentication.

Confirm the required reviewers and branch rules in GitHub before dispatching
either publishing job.

## 3. Prepare and merge the release PR

Sync a feature branch with `main`, update the package version and
[changelog](CHANGELOG.md), and open a PR. Wait for the Windows, macOS, and Linux
test matrix to pass before merging. Review the built archives for the expected
source, typing marker, license, and metadata. Review the dependency audit and
test recovery from an existing vault.

The CI workflow reports a single **PR checks** status for the full matrix.
After it has reported on GitHub, add **PR checks** to the required status checks
in the branch ruleset. Feature pushes run the smoke matrix.

The rehearsal build uses `pip-audit` on the runtime dependencies installed
with the wheel. If it reports a vulnerability, review the advisory, update
the affected dependency, and rerun the audit before approving publication.

## 4. Run and verify TestPyPI

1. Under **Actions → release rehearsal → Run workflow**, select `main` and
   destination `testpypi`. Leave the rehearsal run ID blank.
2. Review the build's commit, wheel, source archive, and SHA256 hashes. Approve
   the `testpypi` deployment under **Review deployments**.
3. Wait for `verify-testpypi` to pass. The verification jobs install the exact
   wheel from TestPyPI on Python 3.10 and 3.14, smoke-test it, and check the
   published wheel and source archive hashes. Python 3.14 also copies and
   reads back a fake password using an isolated X11 clipboard.
4. Follow the [installation guide](USER_GUIDE.md#1-install-clave) in a fresh
   environment and [test a restore](USER_GUIDE.md#11-check-and-recover-your-vault).
   Save the workflow run ID, commit SHA, and both package hashes.

If TestPyPI indexing is delayed, rerun the failed verification job after the
files appear. A changed distribution requires a new version.

## 5. Promote to PyPI

Keep `main` at the rehearsed commit through promotion. Run **release rehearsal**
again from `main`, choose `pypi`, and enter the successful TestPyPI run ID.
Approve the `pypi` deployment after checking the run and artifact hashes.

The workflow requires a successful rehearsal for the same commit on `main`
and uploads its retained wheel and source archive. The artifact is available
for 30 days. After publication, verify the pinned install from production PyPI,
tag the published commit, and clean up the merged feature branches.

## Troubleshooting

| Symptom | Check |
|---|---|
| Missing Run workflow button | workflow_dispatch must exist on the default branch |
| Approval prompt absent | Save required reviewers on the named GitHub environment |
| invalid-publisher / OIDC failure | Exact owner, repository, release.yml and environment on the correct index |
| Deployment rejected | Environment branch restrictions and approval permissions |
| File already exists | Inspect prior uploads and avoid reusing changed version files |
| pip cannot find the release | Check the TestPyPI URL, uploaded version, and indexing delay |

Official references are [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/),
[pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/),
[GitHub environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
and [manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
