# Changelog

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
