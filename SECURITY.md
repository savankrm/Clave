# Security model and limits

Clave V1 protects record payloads if an attacker obtains only the SQLite database.
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

**Losing either the key or database, or corrupting either, can irreversibly lose all
records.** No backup/restore, key migration, rotation or recovery is implemented.
Recovery tooling remains an accepted low-priority V2 risk. Never regenerate a key
for an existing database. The schema, key check, and first entry commit in one
SQLite transaction. On failure before the commit attempt, Clave tries to remove
only the files it created during that attempt. A crash or failed cleanup can
still leave files that require owner inspection. Do not delete files containing
valuable records in an attempt to reset the vault.

There is no supported secure unattended CI/CD distribution/unlock solution, cloud
fallback, OS keychain, passphrase or environment-secret injection. Prompt-free Python
reads require accessible local files, not a TTY. CI for Clave itself uses fake values
under temporary roots. Report security issues privately to the repository owner;
never include actual keys, database payloads, credentials or full argv in reports.
