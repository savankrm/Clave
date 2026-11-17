from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path, user_data_path

from .exceptions import UnsafePath


def safe_path(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    attributes = getattr(info, "st_file_attributes", 0)
    if stat.S_ISLNK(info.st_mode) or (
        os.name == "nt"
        and attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        raise UnsafePath("Refusing a symlink or junction in a vault path.")


def private_dir(path: Path) -> None:
    if not path.parent.exists():
        private_dir(path.parent)
    path.mkdir(mode=0o700, exist_ok=True)


@dataclass(frozen=True)
class Paths:
    database: Path
    key: Path
    roots: tuple[Path, ...]

    def check(self) -> None:
        for path in (*self.roots, self.database.parent, self.key.parent):
            safe_path(path)
        safe_path(self.database)
        safe_path(self.key)

    @classmethod
    def resolve(cls, root: str | Path | None) -> Paths:
        if root is not None:
            base = Path(os.path.abspath(root))
            return cls(
                base / "data" / "vault.sqlite3",
                base / "config" / "vault.key",
                (base,),
            )
        data = Path(os.path.abspath(user_data_path("clave", appauthor=False)))
        config = Path(os.path.abspath(user_config_path("clave", appauthor=False)))
        roots = (data,) if data == config else (data, config)
        if data == config:
            data, config = data / "data", config / "config"
        return cls(data / "vault.sqlite3", config / "vault.key", roots)
