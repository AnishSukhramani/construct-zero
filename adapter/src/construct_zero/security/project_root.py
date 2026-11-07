"""Detect Construct-Zero install root vs the user's project workspace."""

from __future__ import annotations

import os
from pathlib import Path

_NESTED_DIR_NAMES = frozenset({"construct-zero", ".cz"})


def _repo_root_from_package() -> Path:
    # adapter/src/construct_zero/security/project_root.py -> repo root
    return Path(__file__).resolve().parents[4]


def cz_install_root() -> Path:
    raw = (os.environ.get("CZ_ROOT") or os.environ.get("HCX_ROOT") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _repo_root_from_package().resolve()


def is_nested_cz_install(install: Path | None = None) -> bool:
    """True when CZ lives inside a parent repo (e.g. myapp/construct-zero/)."""
    root = (install or cz_install_root()).resolve()
    name = root.name.lower()
    if name in _NESTED_DIR_NAMES:
        return True
    parent = root.parent
    if parent != root and (parent / ".git").exists() and root != parent:
        return True
    return False


def resolve_user_project_root(cwd: Path | None = None) -> Path:
    """
    Directory Hermes and Cursor should treat as the project workspace.

    Prefers ``CZ_PROJECT_ROOT``, then walks up from ``cwd`` when the install is
    nested under a parent repository.
    """
    explicit = (
        os.environ.get("CZ_PROJECT_ROOT") or os.environ.get("HCX_PROJECT_ROOT") or ""
    ).strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    start = (cwd or Path.cwd()).resolve()
    install = cz_install_root()

    if install == start or install in start.parents:
        if is_nested_cz_install(install):
            return install.parent.resolve()
        return install

    if is_nested_cz_install(install) and start == install.parent:
        return start.resolve()

    return start


def agent_context_is_cz_source(project: Path | None = None) -> bool:
    """True when the resolved project root is the CZ install tree (misconfiguration)."""
    proj = (project or resolve_user_project_root()).resolve()
    install = cz_install_root().resolve()
    if proj != install:
        return False
    return is_nested_cz_install(install)


def relative_cz_install_path(project: Path | None = None) -> str | None:
    """Path from project root to the CZ install, for ignore-file entries."""
    proj = (project or resolve_user_project_root()).resolve()
    install = cz_install_root().resolve()
    try:
        rel = install.relative_to(proj)
    except ValueError:
        return None
    return rel.as_posix()
