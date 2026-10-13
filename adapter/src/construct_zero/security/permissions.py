"""Restrictive permissions for Construct-Zero state on disk."""

from __future__ import annotations

import os
from pathlib import Path

DIR_MODE = 0o700
FILE_MODE = 0o600


def ensure_secure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, DIR_MODE)
    except OSError:
        pass


def ensure_secure_file(path: Path, *, create: bool = False) -> None:
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()
    if path.is_file():
        try:
            os.chmod(path, FILE_MODE)
        except OSError:
            pass
