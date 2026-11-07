"""State directory permissions."""

from __future__ import annotations

from pathlib import Path

from construct_zero.security.permissions import ensure_secure_dir, ensure_secure_file


def test_secure_dir_and_file_modes(tmp_path: Path) -> None:
    d = tmp_path / "state"
    ensure_secure_dir(d)
    assert oct(d.stat().st_mode & 0o777) == oct(0o700)
    f = d / "admin.key"
    ensure_secure_file(f, create=True)
    assert oct(f.stat().st_mode & 0o777) == oct(0o600)
