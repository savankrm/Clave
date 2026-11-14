from dataclasses import dataclass, field
from typing import Literal

EntryType = Literal["credential", "secret"]


@dataclass(frozen=True)
class Credential:
    username: str = field(repr=False)
    password: str = field(repr=False)


@dataclass(frozen=True)
class StoreResult:
    action: Literal["created", "replaced"]
    vault_created: bool = False


@dataclass(frozen=True)
class EntryMetadata:
    id: str
    environment: str | None
    entry_type: EntryType
    created_at: str
    updated_at: str
