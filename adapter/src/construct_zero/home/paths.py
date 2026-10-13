"""Resolve Construct-Zero state and project paths."""

from __future__ import annotations

import os
from pathlib import Path


def cz_state_dir() -> Path:
    """Per-install state directory (registry, usage, budgets)."""
    raw = os.environ.get("CZ_STATE_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".construct-zero" / "state"


def cz_root() -> Path | None:
    raw = os.environ.get("CZ_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser()
    return None


def project_cz_dir(project: Path | None = None) -> Path:
    root = project or Path.cwd()
    return root.resolve() / ".cz"
