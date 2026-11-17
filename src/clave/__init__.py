"""Public interfaces for Clave's local credential vault."""

from .exceptions import (
    BackupError,
    ClaveError,
    EntryAlreadyExists,
    EntryNotFound,
    EntryTypeMismatch,
    IncompleteVault,
    InvalidIdentifier,
    InvalidValue,
    UnsafePath,
    UnsupportedSchema,
    VaultCorrupt,
    VaultNotInitialized,
)
from .models import Credential, EntryMetadata, StoreResult
from .vault import Vault

__all__ = [
    "BackupError",
    "ClaveError",
    "Credential",
    "EntryAlreadyExists",
    "EntryMetadata",
    "EntryNotFound",
    "EntryTypeMismatch",
    "IncompleteVault",
    "InvalidIdentifier",
    "InvalidValue",
    "StoreResult",
    "UnsafePath",
    "UnsupportedSchema",
    "Vault",
    "VaultCorrupt",
    "VaultNotInitialized",
]
