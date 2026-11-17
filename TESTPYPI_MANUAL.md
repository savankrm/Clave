# Clave publishing manual — starting with code on GitHub

This guide assumes you know only that the Clave code has reached GitHub.
Follow the numbered steps to understand the setup, approve a practice release,
and install and verify the result on Windows. Each step gives its purpose and
expected result. Account setup is done once. Installation can be repeated.

If clave 0.1.0 is already published on TestPyPI, read the explanations and start
the hands-on installation at Step 14. Repeat uploads require maintainer review
because an existing version's uploaded files cannot be replaced.

## The words you will see

| Word | Meaning in this guide |
|---|---|
| Repository | The project's files and change history on GitHub |
| Branch | A named line of work, such as release/clave-0.1.0 or main |
| Commit | A saved change identified by letters and numbers |
| Push | Sending local commits to GitHub |
| Actions | GitHub's service for automatically running tasks |
| Workflow | A saved set of automated instructions |
| Run | One execution of a workflow for a particular commit |
| Job | A group of steps, such as building or uploading |
| Step | One task within a job |
| Runner | The GitHub computer executing a job |
| Matrix | Repeating a job with different operating systems or Python versions |
| Environment | Named deployment rules, including who can approve publication |
| Deployment | A workflow job using a named environment to publish something |
| Artifact | Files saved by a workflow run for download or later use |
| Wheel | The .whl file pip installs |
| Source archive | The .tar.gz file containing buildable project sources |
| pip | Python's package installation tool |
| TestPyPI | The practice package website at test.pypi.org |
| PyPI | The package website used by normal pip installations |
| Trusted Publisher | An account setting authorizing a particular GitHub workflow to upload |
| Pull request / PR | A proposed branch change submitted for review before merging |

GitHub environment rules apply to publication jobs. The local Python environment
created later is a separate folder containing an isolated package installation.

## What happens from start to finish

```text
Code pushed to the release branch
  -> checks workflow tests Windows, macOS and Linux
  -> release rehearsal builds installable files
  -> testpypi environment waits for a person's approval
  -> approved files upload to TestPyPI
  -> verify-testpypi downloads and checks the uploaded package
  -> you install it in a fresh Windows environment and verify it
  -> maintainer records results and prepares a pull request for owner review
```

Production publication has its own pypi environment and a separately approved
manual run. This walkthrough finishes with the practice release and verification.

## Step 1 — Open the repository and release branch

**Purpose:** Confirm you are looking at the correct project and saved release code.

1. Open https://github.com/savankrm/Clave and sign in.
2. Click **Code** near the top.
3. Open the branch dropdown, which may currently say main.
4. Search for and select **release/clave-0.1.0**.
5. Note the latest commit shown above the file list. Click it to see its saved changes.

**Expected:** Files such as README.md, pyproject.toml, src and tests appear on the
release branch. If main contains fewer files, return to the release branch.
The branch can be reviewed and tested before its pull request is merged.

## Step 2 — Find the automation instructions

**Purpose:** Understand where GitHub gets the tasks it runs after code is pushed.

In the repository's file list, open **.github**, then **workflows**.
Open each file below to read its contents. Return using the browser's Back button.

| File | Displayed workflow | Function |
|---|---|---|
| ci.yml | checks | Runs code checks and compatibility tests |
| release.yml | release rehearsal | Builds files, uploads to TestPyPI after approval, then verifies installation |

These files contain YAML, a text format for workflow settings. The maintainer
writes and validates these instructions. A reviewer can follow this manual
without editing YAML. If a file is missing, ask the maintainer to check the branch
and confirm it was pushed.

**Expected:** Both workflow files are visible on the release branch.

## Step 3 — Understand the checks and jobs

**Purpose:** Know what each result proves before approving the package upload.

Click **Actions** at the top, select **checks** on the left, and open a run for
the release branch. Its test job is repeated for Python 3.10 through 3.15 on
Windows, macOS and Linux, giving 18 combinations.

Click a job such as **test (windows-latest, 3.10)** to expand its steps.

| Check or action | Purpose |
|---|---|
| Checkout | Copies that commit's code onto the runner |
| Setup Python | Selects the Python version for the job |
| Install dependencies | Installs the libraries and tools needed by the project |
| Ruff lint | Finds common coding mistakes |
| Ruff format | Checks consistent source formatting |
| Strict mypy | Checks annotated types, targeting Python 3.10 compatibility |
| pytest with coverage | Runs behavior tests and measures how much code they execute |
| Build | Creates the wheel and source archive |
| Twine check | Validates package metadata and its description |
| Installed-wheel smoke | Installs the built package and exercises its CLI and API |

Now select **release rehearsal** on the left. It has these jobs.

| Job | Function and dependency |
|---|---|
| build | Runs checks on Ubuntu/Python 3.10, builds files and saves the artifact |
| testpypi | Waits for build and environment approval, then uploads |
| verify-testpypi | Waits for upload, then downloads, compares, installs and tests the wheel |
| pypi | Later production promotion, eligible only for a manual pypi run on main |

**Expected:** You can identify which workflow checks compatibility and which
workflow publishes the package. A green job confirms its own checks passed.
A skipped or cancelled job has no passing result for that attempt. Any accepted
exception should be recorded explicitly by the owner.

The checks workflow continues its other matrix jobs even if one fails, so the
maintainer can inspect every platform's result. The release workflow has its own
build checks and runs independently of that 18-job matrix. Review the intended
commit's checks before approving publication and record any owner-accepted waiver.

The workflow also limits access for each job.

| Setting | Why it is used |
|---|---|
| contents read | Lets build and verification retrieve repository code |
| id-token write | Lets the publishing job request temporary identity credentials |
| actions read in production | Lets promotion retrieve artifacts from the selected rehearsal |
| Publication concurrency | Queues another publication run until the current one finishes |

Each job receives only the listed access it needs. The maintainer sets these
permissions in release.yml. The reviewer configures approval rules in repository
Settings. Saving a workflow file with an environment name alone does not create
its required-reviewer rules.

## Step 4 — Prepare the package-index accounts

**Purpose:** The publishing owner needs an account on each website that receives
packages, with email verification and two-factor authentication completed.

1. Open https://test.pypi.org/account/register/ to create the practice account,
   or sign in if it already exists.
2. Complete email verification and configure two-factor authentication when prompted.
3. Save recovery codes securely using your normal account-recovery process.
4. For future production setup, repeat on https://pypi.org/account/register/.

**Expected:** The owner can sign in to both separate accounts.
GitHub login alone does not create these accounts. Local installation of a public
TestPyPI package does not require signing in.

## Step 5 — Create the GitHub approval environments

**Purpose:** Environment rules decide who must approve an upload and which branch
may publish. Configure these before starting the publishing workflow.

1. Open https://github.com/savankrm/Clave/settings/environments as the owner.
2. Click **New environment**, enter **testpypi**, then **Configure environment**.
3. Enable **Required reviewers**, search for **savankrm** and select that account.
4. Leave **Prevent self-review** unchecked for this single-owner setup.
5. Disable **Allow administrators to bypass configured protection rules** if shown.
6. Click **Save protection rules**.
7. Under **Deployment branches and tags**, choose **Selected branches and tags**.
8. Click **Add deployment branch or tag rule**. Choose **Branch**, enter exactly
   **release/clave-0.1.0**, then click **Add rule**.
9. Repeat for **pypi**, using **main** as its permitted branch.

**Expected:** Each environment shows its required reviewer and permitted branch.
Leave environment secrets and variables empty for this publishing setup.
If the environments already exist, inspect and correct their rules instead of
recreating them. If Settings is unavailable, ask the repository owner to do this.

## Step 6 — Tell TestPyPI which workflow to trust

**Purpose:** The publisher setting lets TestPyPI recognize the authorized GitHub
workflow and environment when it requests temporary upload credentials.

1. Sign in at https://test.pypi.org.
2. Open account settings, then **Publishing**, or use
   https://test.pypi.org/manage/account/publishing/.
3. If the project has never been published, use **Add a new pending publisher**
   and select the GitHub form.
4. Enter the following values and click **Add**.

| Field | Value |
|---|---|
| PyPI project name | clave |
| GitHub owner | savankrm |
| Repository | Clave |
| Workflow filename | release.yml |
| Environment name | testpypi |

**Expected:** The pending publisher lists savankrm/Clave, release.yml and testpypi.
Check the spelling testpypi carefully. The workflow filename field takes release.yml.
The repository file itself is located at .github/workflows/release.yml.

A pending publisher creates the project when its first upload succeeds. It does
not reserve the package name. After publication, use the project's **Manage** page
and **Publishing** settings to inspect its existing publisher.

For future production setup, use the production PyPI account's Publishing page
with the same project, owner, repository and workflow, and environment **pypi**.
No permanent PyPI token is needed for this Trusted Publishing workflow.

## Step 7 — Understand how the rehearsal starts

**Purpose:** Know which push starts a release so you can locate the correct run
and avoid unintentionally repeating an existing version's upload.

The maintainer has already supplied release.yml. With the environment and publisher
configured, a push on release/clave-0.1.0 changing release.yml or PUBLISHING.md
starts the release rehearsal automatically. The checks workflow also runs.
You do not have to create jobs in the Actions screen.

If a run is already present, use it. Ask the maintainer before starting another
publication of 0.1.0. When **Run workflow** is available, choose the release branch,
select destination **testpypi** and leave rehearsal_run_id empty for rehearsal.
That field is used later for approved production promotion.

**Expected:** A release rehearsal run is listed for the intended commit.
If **Run workflow** is absent, the workflow may still exist only on the release
branch. GitHub requires it on the default branch for manual dispatch. The existing
release-branch push trigger allows the first rehearsal before that merge.

## Step 8 — Read progress, errors and saved files

**Purpose:** Learn where to look when a job waits, succeeds or fails, and where
the built package files are retained for review.

1. Click a workflow run, then click a job to view its steps.
2. Expand a step to read its log, the text output describing what happened.
3. For a failure, copy the error and the full run URL to the maintainer.
4. On the run's summary page, find **Artifacts** after build finishes.
5. The **clave-distributions** artifact contains the .whl and .tar.gz files.
   Click its name if you want to download them for inspection.

| Status | What it means and what you do |
|---|---|
| Queued | Waiting for a runner. Allow time for capacity |
| In progress | Working. Open the job to see its current step |
| Waiting for review | A configured reviewer must approve the environment |
| Green / Success | That job's steps completed successfully |
| Red / Failure | Inspect the failed step before proceeding |
| Skipped | Its condition or dependency prevented execution |
| Cancelled | Execution was stopped and cannot be counted as a pass |

The build logs print SHA256 hashes, identifiers derived from each file's contents.
The verify-testpypi job compares the downloaded wheel with the built file.
Artifacts in this workflow are retained for 30 days. They are distinct from the
package release hosted on TestPyPI.

**Expected:** You can find the status, error details and built files without editing code.
Continue below for approval, publication and local verification.

## Step 9 — Find the release run

**Purpose:** GitHub Actions runs the checks and creates the package files.

1. Open https://github.com/savankrm/Clave/actions and sign in.
2. Select **release rehearsal** on the left.
3. Open the intended run for **release/clave-0.1.0**. Check its commit matches
   the release the maintainer asked you to review.

**Expected:** A summary containing build, testpypi and verify-testpypi jobs.
The pypi job is skipped during this practice release.

This workflow starts when a push to the release branch changes PUBLISHING.md or
.github/workflows/release.yml. Other pushes may start only the checks workflow.
If no rehearsal run exists, ask the maintainer to confirm the workflow was pushed.
The **Run workflow** button is available once the manual workflow exists on the
default branch. When available, choose the release branch and destination testpypi.

## Step 10 — Wait for the build

**Purpose:** The build tests the code and checks the package before uploading it.

Click **build** to watch progress. Wait for its green check mark.
Queued means it is waiting for a GitHub computer. In progress means it is running.
If it turns red, send the failed step's error and the run URL to the maintainer.

**Expected:** build is green and testpypi waits for approval.

## Step 11 — Approve the practice upload

**Purpose:** Your approval authorizes this particular upload to TestPyPI.
GitHub supplies temporary publishing credentials automatically.

1. Return to the run summary and click **Review deployments**.
2. Select **testpypi** and confirm the branch and commit.
3. Click **Approve and deploy**.

**Expected:** testpypi starts. Only a configured reviewer can approve the job.
If the button is missing, check whether the job is still queued, already approved
or finished. Ask the owner to check the environment rules if needed.

## Step 12 — Check the TestPyPI upload

**Purpose:** This sends the package files to the practice index for installation.

Wait for **testpypi** to turn green, then open
https://test.pypi.org/project/clave/0.1.0/.

**Expected:** The page shows clave, version 0.1.0. Allow a minute or two for indexing.
If you see invalid-publisher, ask the owner to check the repository, release.yml
filename and testpypi environment in the TestPyPI publisher settings.
If you see File already exists, ask the maintainer to inspect the previous upload.
Changed package files require a new version, including on TestPyPI.

## Step 13 — Check automated installation

**Purpose:** GitHub downloads the uploaded wheel, compares it with the built file,
and tests it in a clean environment.

Open **verify-testpypi** in the same run and wait for a green check mark.

**Expected:** build, testpypi and verify-testpypi are green. pypi is skipped.
If only verification failed after upload, send its error to the maintainer.
After an indexing delay, rerunning just that failed job may be sufficient.
Rerunning the upload can fail because the version files already exist.

## Step 14 — Open PowerShell and find Python

**Purpose:** These commands select the Python program used for the local test.

Open Windows PowerShell and run the following block.

```powershell
$taskPython = 'C:\Users\Savan\AppData\Local\Python\pythoncore-3.15-64\python.exe'
& $taskPython --version
```

**Expected:** Python 3.10 or newer. This computer uses Python 3.15.2.
On another computer, replace the quoted path with its Python executable location.
Keep this PowerShell window open so its variables remain available.

## Step 15 — Create a fresh practice environment

**Purpose:** This gives the downloaded package its own installation folder,
independent of the development installation.

```powershell
Set-Location E:\Clave
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
$reviewRoot = 'E:\Clave\.smoke\manual-testpypi-review'
& $taskPython -m venv $reviewRoot
$reviewPython = Join-Path $reviewRoot 'Scripts\python.exe'
$claveCommand = Join-Path $reviewRoot 'Scripts\clave.exe'
```

**Expected:** Commands finish without errors. Little or no output is normal.
For a fresh repeat, change manual-testpypi-review to manual-testpypi-review2.
These commands use the environment's programs directly. Activation and changes
to PowerShell's script execution policy are unnecessary.

## Step 16 — Install supporting packages

**Purpose:** Clave needs encryption, command-line and folder-location libraries.
This installs them from the normal Python package index.

```powershell
& $reviewPython -m pip install 'cryptography>=46' 'typer>=0.29,<0.30' 'platformdirs>=4'
```

**Expected:** Successfully installed. A pip update notice is informational.
Resolve any installation error before proceeding.

## Step 17 — Install Clave from TestPyPI

**Purpose:** This downloads Clave 0.1.0 from the practice index. The --no-deps
option uses the supporting packages installed in Step 16.

```powershell
& $reviewPython -m pip install --index-url https://test.pypi.org/simple/ --no-deps 'clave==0.1.0'
```

**Expected:** Successfully installed clave-0.1.0.
If it says Requirement already satisfied, use a new folder name in Step 15 when
you want to prove a fresh download and installation.

## Step 18 — Verify the version and command

**Purpose:** This confirms the installed version, where it loads from, and whether
the command-line program starts successfully.

```powershell
& $reviewPython -c "from importlib.metadata import version; import clave; print(version('clave')); print(clave.__file__)"
& $claveCommand --help
```

**Expected:** Version 0.1.0, a path beneath your review folder's Lib\site-packages,
and a help screen listing the available commands.

## Step 19 — Store a fake secret

**Purpose:** This checks that Clave creates encrypted storage and saves a value.
The custom folder keeps the practice vault separate from everyday data.

```powershell
$demoVault = Join-Path $reviewRoot 'demo-vault'
& $claveCommand --data-dir $demoVault secret store demo_token
```

At the hidden prompt, type **demo-only-123** and press Enter. The characters stay
hidden while you type.

**Expected:** Secret created for demo_token, plus a vault-creation notice on the
first write. Repeating the store may report Secret replaced.

## Step 20 — Inspect the saved entry

**Purpose:** This checks that the CLI finds the entry while keeping its value hidden.

```powershell
& $claveCommand --data-dir $demoVault secret get demo_token
& $claveCommand --data-dir $demoVault list
```

**Expected:** demo_token, type secret and global scope information.
The sample value demo-only-123 should stay absent from the output.

## Step 21 — Verify the Python API

**Purpose:** Applications use the Python API to retrieve saved values.
This checks the sample value and prints only a success message.

```powershell
$checkCode = @"
import sys
from clave import Vault
vault = Vault(data_dir=sys.argv[1])
if vault.get_secret('demo_token') != 'demo-only-123':
    raise SystemExit('Verification failed. Store the sample value again.')
print('PASS: Python retrieved the expected sample value.')
"@
& $reviewPython -c $checkCode $demoVault
```

**Expected:** PASS: Python retrieved the expected sample value.
If you entered a different value, repeat Step 19 using demo-only-123.

## Step 22 — Check deletion confirmation

**Purpose:** This verifies that Clave asks permission before removing an entry.

```powershell
& $claveCommand --data-dir $demoVault delete demo_token
```

Type **y** and press Enter when asked.

**Expected:** The entry is deleted. Running secret get demo_token again reports
that it does not exist. That final error is expected after deletion.
Deletion removes the entry from normal use but does not guarantee forensic erasure.

## Step 23 — Record your results

**Purpose:** These details let the maintainer confirm the rehearsal and prepare
its status update and pull request for owner review.

| Item | What to record |
|---|---|
| GitHub run | Full Actions run URL |
| Source | Release branch and commit shown in the run |
| Upload | Whether testpypi is green |
| Automated verification | Whether verify-testpypi is green |
| Package page | https://test.pypi.org/project/clave/0.1.0/ |
| Local Python | Version from Step 14 |
| Installed package | Version and import location from Step 18 |
| Local checks | Help, store, metadata read, API verification and deletion results |

Send those results to the maintainer. Production publication requires the owner's
separate approval after review.

## Quick help

| Problem | What to do |
|---|---|
| Activate.ps1 is blocked | Use the executable variables from Step 15 |
| Variables disappeared after reopening PowerShell | Repeat Steps 6 and 7 |
| No matching distribution for clave | Check version, TestPyPI package page and upload result |
| No module named clave | Use $reviewPython from the practice environment |
| CLI get hides the token | Expected. Step 21 verifies the value through Python |
| Entry missing after deletion | Expected. Store it again to repeat the exercise |
| A GitHub job is red | Send its error message and run URL to the maintainer |

Account setup is covered in [PUBLISHING.md](PUBLISHING.md).
Approval controls are explained in [GitHub's deployment review guide](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments).
Index installation is explained in [PyPA's TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/).

Further background is available in [GitHub Actions concepts](https://docs.github.com/en/actions/get-started/understand-github-actions), [environment configuration](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments), and [PyPI pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
