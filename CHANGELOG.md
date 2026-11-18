# Changelog

## 0.2.2

- Export and import encrypted vault archives with `clave export` and `clave import`.
- Rotate the active vault key in place with `clave rotate-key` or on the next
  credential operation after 15 days. Recover interrupted rotations on the next use.
- Enforce private POSIX permissions before initializing or accessing a vault.

## 0.2.1

- Search entry names with `clave find` or **View entries** in the menu.
- Copy credential passwords with `clave copy` and see a clipboard-history warning.
- Move artifact uploads, downloads, and PyPI rehearsal validation to GitHub
  Actions versions that use Node.js 24.
- Run push smoke checks on Windows, macOS, and Linux using the latest stable
  Python 3.
- Put usable install steps first and link the quick start to the pytest example.
- Test safe backup failures for a full disk and filesystems without hard links.
- Audit release dependencies and verify the TestPyPI wheel on Python 3.10 and
  3.14, including a clipboard check on an isolated X11 display.
- Report a single PR status for the cross-platform test matrix.

## 0.2.0

### Vault and CLI

- Open the interactive vault menu when `clave` runs without a command in a terminal.
- Show asterisks as users type credential passwords in the CLI and the menu.
- Ask for confirmation before CLI overwrites. Use `--replace` to skip the prompt
  or replace an entry from a script.
- Add read-only vault diagnostics and passphrase-protected backup and restore to a fresh vault.
- Explain missing vault files and deletion limits in plain language.

- Create the SQLite schema, key check, and first vault entry in a single
  transaction. A failure before the commit attempt triggers cleanup of newly
  created files where possible. Each operation loads the vault key once.
- Allow redirected directories above the vault while rejecting symlinks and
  junctions at the vault root, storage directories, and files. Preserve existing
  directory permissions and support paths containing SQLite URI characters.
- Validate IDs and usernames before prompting for secrets. Keep each invocation's
  vault in its command context and report missing arguments without echoing input.
- Export `Vault`, public exceptions, and return types at the package root.

### Packaging, tests, and documentation

- Clarify the TestPyPI release status and show a complete save-and-retrieve quick start.

- Limit the source distribution to package code, tests, and essential build and
  licensing files. Expand Git ignore rules for local secret and build artifacts.
- Widen Typer support to `>=0.28,<1.0`, require `cryptography>=50.0.2`, and add
  package keywords and classifiers for PyPI discovery.
- Add focused Fernet and identifier tests. Run the [pytest login example](examples/README.md)
  in CI to verify the documented fixture with fake credentials.
- Update checkout in both workflows to `actions/checkout@v7.0.1` on Node.js 24.
- Run the full test matrix on pull requests and an installation smoke check on pushes.
- Run both publishing destinations manually from `main`. Production uses the
  distributions verified on TestPyPI for the same commit.

## 0.1.0 — release candidate

### Features

- Local encrypted credential and secret storage using Fernet and SQLite.
- Automatic vault creation on the first successful store.
- Credential identifiers with topic and environment, plus global and scoped secrets.
- Whole-value replacement for existing entries of the same type.
- Python Vault API and command-line commands for storing, inspecting and deleting.
- Hidden input prompts, metadata-only CLI reads and explicit deletion confirmation.
- Python 3.10 and newer support with Windows, macOS and Linux CI coverage.

### Security and compatibility verification

- Automated tests cover initialization safety, corruption, tampering, type
  collisions, replacement rollback, concurrent access and secret disclosure.
- Local validation passed lint, formatting, strict Python-3.10-targeted typing,
  tests, package builds, strict package validation and installed-wheel smoke checks.
- The local test suite reported 45 passed, one expected Windows skip for POSIX
  permission checks and 99% statement coverage.
- The final observed Day 4 run had 16 successful jobs and two cancelled macOS jobs.
  The owner accepted a waiver for delayed macOS runners during that checkpoint.
- Corrected platform-specific stat attribute access and macOS temporary-path
  handling found during cross-platform checks.

### Release rehearsal

- Added an approval-gated Trusted Publishing workflow and a first-time publisher guide.
- Published clave 0.1.0 to TestPyPI and verified installation into a fresh local
  Python environment, including native CLI and encrypted API smoke checks.
- Production release remains pending owner review and approval.

See [SECURITY.md](SECURITY.md) for the security model and recovery limitations,
and [PUBLISHING.md](PUBLISHING.md) for the release process.
