"""Nonrevealing public failures."""


class ClaveError(Exception):
    """Base class for expected vault failures."""


class InvalidIdentifier(ClaveError):
    pass


class InvalidValue(ClaveError):
    pass


class VaultNotInitialized(ClaveError):
    pass


class IncompleteVault(ClaveError):
    pass


class VaultCorrupt(ClaveError):
    pass


class UnsupportedSchema(ClaveError):
    pass


class UnsafePath(ClaveError):
    pass


class EntryNotFound(ClaveError):
    pass


class EntryAlreadyExists(ClaveError):
    pass


class EntryTypeMismatch(ClaveError):
    pass


class BackupError(ClaveError):
    pass
