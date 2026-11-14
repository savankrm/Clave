from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path, user_data_path

from .exceptions import UnsafePath


def safe_path(path: Path) -> None:
    for candidate in (path, *path.parents):
        try:
            attributes = candidate.lstat().st_file_attributes
        except (AttributeError, FileNotFoundError):
            attributes = 0
        if candidate.is_symlink() or (
            os.name == "nt"
            and attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise UnsafePath("Refusing a symlink or junction in a vault path.")


def private_dir(path: Path) -> None:
    safe_path(path)
    if not path.parent.exists():
        private_dir(path.parent)
    path.mkdir(mode=0o700, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)


@dataclass(frozen=True)
class Paths:
    database: Path
    key: Path

    @classmethod
    def resolve(cls, root: str | Path | None) -> Paths:
        if root is not None:
            base = Path(root).absolute()
            return cls(base / "data" / "vault.sqlite3", base / "config" / "vault.key")
        data = user_data_path("clave", appauthor=False)
        config = user_config_path("clave", appauthor=False)
        if data == config:
            data, config = data / "data", config / "config"
        return cls(data / "vault.sqlite3", config / "vault.key")
