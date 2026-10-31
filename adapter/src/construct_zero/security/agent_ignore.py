"""Recommend agent ignore rules so CZ install files stay out of context."""

from __future__ import annotations

from pathlib import Path

from construct_zero.security.project_root import cz_install_root, relative_cz_install_path

IGNORE_MARK = "# construct-zero: ignore install tree (do not remove)"
IGNORE_FILES = (".cursorignore", ".clineignore")
HERMES_EXCLUDE = ".hermes/context-exclude.txt"

DEFAULT_LINES = (
    "construct-zero/",
    ".cz/",
    "hermes/",
    ".construct-zero/",
    ".hermes/",
    ".venvs/",
)


def _append_unique_lines(path: Path, lines: list[str]) -> bool:
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if IGNORE_MARK in existing:
        return False
    block = "\n".join([IGNORE_MARK, *lines, ""]) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + block, encoding="utf-8")
    return True


def ensure_agent_ignore_files(project: Path | None = None) -> list[str]:
    """Write ignore entries under the user project root. Returns paths touched."""
    proj = (project or cz_install_root().parent).resolve()
    rel = relative_cz_install_path(proj)
    lines = list(DEFAULT_LINES)
    if rel and rel not in lines:
        lines.insert(0, f"{rel}/")
    touched: list[str] = []
    for name in IGNORE_FILES:
        p = proj / name
        if _append_unique_lines(p, lines):
            touched.append(str(p.relative_to(proj)))
    hermes_path = proj / HERMES_EXCLUDE
    if _append_unique_lines(hermes_path, lines):
        touched.append(str(hermes_path.relative_to(proj)))
    return touched
