"""Admin key and kill-switch flag."""

from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path

from construct_zero.home.paths import cz_state_dir


def admin_key_path() -> Path:
    return cz_state_dir() / "admin.key"


def killed_flag_path() -> Path:
    return cz_state_dir() / "killed"


def ensure_admin_key() -> str:
    path = admin_key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(32)
    path.write_text(key + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return key


def verify_admin_key(provided: str | None) -> bool:
    if not provided:
        return False
    if provided.lower().startswith("bearer "):
        provided = provided.split(" ", 1)[1].strip()
    expected = ensure_admin_key()
    return hmac.compare_digest(provided, expected)


def is_killed() -> bool:
    return killed_flag_path().is_file()


def set_killed(reason: str = "") -> None:
    p = killed_flag_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(reason or "killed\n", encoding="utf-8")


def clear_killed() -> None:
    p = killed_flag_path()
    if p.is_file():
        p.unlink()
