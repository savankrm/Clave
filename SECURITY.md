# Security model and limits

Clave protects record payloads if an attacker obtains only the SQLite database.
It does not protect against theft of both files, local-account compromise, malware,
debuggers, hostile Python code, compromised sessions or memory inspection. File
separation is not a trust boundary. Explicit API values are plaintext in memory.

Clave generates a fresh random Fernet key and stores it outside SQLite. Stored
passwords are encrypted values. They never serve as inputs to key generation, so
this design requires neither a password KDF nor a salt file. The first successful
store initializes the vault using exclusive file
creation; package installation does not create user data. Initialization refuses
partial vaults. A versioned encrypted sentinel detects wrong keys before CRUD. Payloads
are authenticated versioned JSON, not pickle; unsupported schemas fail closed.
Metadata (topic, optional environment, type, timestamps, schema) and database
structure are plaintext. Global secrets use an internal empty environment; scoped
secrets and credentials expose their environment. Fernet tokens expose their
creation timestamp. Encryption is per record, not whole-database encryption.

POSIX application directories are created with mode 0700; key/database files with
0600. SQLite sidecars inherit database restrictions. Windows relies on appropriately
restricted user-profile ACLs: chmod is not a Windows security guarantee. Custom
roots must also have appropriate ACLs. Clave rejects symlinks and junctions at
the vault root, storage directories, and storage files. Ancestors above the vault
root may be redirected by the operating system or user. Existing directory
permissions are left intact. These checks do not defend against a hostile
same-user process racing filesystem changes. Do not share the vault directory.

SQLite transactions serialize competing writes, preserve original creation times
and roll back failed replacement. This is not forensic secure deletion. Filesystem
snapshots, storage remnants, memory and external logs are outside Clave's control.
CLI reads never intentionally emit passwords or secret values. Positional values
can already be exposed by shell history/process listings before Clave starts.
Python callers must not log plaintext returns or credential fields.
The explicit `clave copy` command sends a credential password to the system
clipboard. Other applications, clipboard history, and clipboard sync may retain
it beyond the current session.

The first store commits the schema, key check, and entry in one SQLite transaction.
Restore commits the schema, key check, and all recovered entries together. On
failure before the commit attempt, Clave tries to remove
only the files it created during that attempt. A crash or failed cleanup can
still leave files that require owner inspection. Do not delete files containing
valuable records in an attempt to reset the vault.

**Losing the key or database, or corrupting either, can irreversibly lose records
without a usable backup.** Backups from this checkout contain an authenticated,
encrypted snapshot of entry data and metadata. A separate passphrase derives the
archive encryption key using scrypt with a random salt. The archive envelope
exposes its format, size, salt, and Fernet creation time. An attacker with a copy
can attempt to guess the passphrase offline. Clave accepts at least 12 characters.
Use a password manager to generate a long, unique passphrase and store it
separately from the archive. Clave cannot recover a forgotten
passphrase. The original vault key is absent from the archive. Restore creates a
new key in a fresh vault. See the [recovery guide](USER_GUIDE.md#11-check-and-recover-your-vault).

There is no supported secure unattended CI/CD distribution/unlock solution, cloud
fallback, OS keychain, passphrase or environment-secret injection. Prompt-free Python
reads require accessible local files, not a TTY. CI for Clave itself uses fake values
under temporary roots. Report security issues privately to the repository owner;
never include actual keys, database payloads, credentials or full argv in reports.
