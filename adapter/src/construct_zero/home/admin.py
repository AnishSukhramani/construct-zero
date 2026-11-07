"""Admin key and kill-switch flag."""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path

from construct_zero.home.paths import cz_state_dir
from construct_zero.security.permissions import ensure_secure_dir, ensure_secure_file


def admin_key_path() -> Path:
    return cz_state_dir() / "admin.key"


def killed_flag_path() -> Path:
    return cz_state_dir() / "killed"


def ensure_admin_key() -> str:
    path = admin_key_path()
    ensure_secure_dir(path.parent)
    if path.is_file():
        ensure_secure_file(path)
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(32)
    path.write_text(key + "\n", encoding="utf-8")
    ensure_secure_file(path)
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
    ensure_secure_dir(p.parent)
    p.write_text(reason or "killed\n", encoding="utf-8")
    ensure_secure_file(p, create=True)


def clear_killed() -> None:
    p = killed_flag_path()
    if p.is_file():
        p.unlink()
