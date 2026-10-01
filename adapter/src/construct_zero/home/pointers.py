"""Managed pointer blocks in AGENTS.md, CLAUDE.md, and `.cursor/rules/cz-home.mdc`."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

MARKER_START = "<!-- cz:home:start -->"
MARKER_END = "<!-- cz:home:end -->"

AGENTS_BLOCK = f"""{MARKER_START}
Shared CZ context lives in `.cz/`. Read `.cz/CONTEXT.md`, `.cz/MEMORY.md`, and `.cz/checkpoint.md` first.
Write decisions to `.cz/DECISIONS.md` and update `.cz/checkpoint.md` before you stop.
{MARKER_END}"""

CLAUDE_BLOCK = f"""{MARKER_START}
Shared CZ context (read first):

@.cz/CONTEXT.md
@.cz/MEMORY.md
@.cz/checkpoint.md

Write decisions to `.cz/DECISIONS.md` and update `.cz/checkpoint.md` before you stop.
{MARKER_END}"""

CURSOR_RULE_BODY = """---
description: Construct-Zero shared context home pointers
alwaysApply: true
---

""" + f"""{MARKER_START}
Shared CZ context lives in `.cz/`. Read `.cz/CONTEXT.md`, `.cz/MEMORY.md`, and `.cz/checkpoint.md` first.
Write decisions to `.cz/DECISIONS.md` and update `.cz/checkpoint.md` before you stop.
{MARKER_END}"""

HERMES_MEMORY_LINE = (
    "CZ shared context: read .cz/CONTEXT.md, .cz/MEMORY.md, .cz/checkpoint.md (construct-zero home)."
)


def _managed_block(content: str) -> str | None:
    if MARKER_START not in content or MARKER_END not in content:
        return None
    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(0) if m else None


def _insert_or_replace(path: Path, block: str) -> bool:
    """Return True if file content changed."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        existing = _managed_block(text)
        if existing == block:
            return False
        if existing:
            new_text = text.replace(existing, block)
        else:
            sep = "\n\n" if text.endswith("\n") or not text else "\n\n"
            new_text = text.rstrip() + sep + block + "\n"
    else:
        new_text = block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return True


def _remove_block(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    existing = _managed_block(text)
    if not existing:
        return False
    new_text = text.replace(existing, "").strip() + "\n"
    path.write_text(new_text, encoding="utf-8")
    return True


def is_git_tracked(project: Path, rel: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(project), "ls-files", "--error-unmatch", rel],
            capture_output=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


def git_exclude_cz(project: Path, *, commit_mode: bool) -> None:
    if commit_mode:
        return
    git_dir = project / ".git"
    if not git_dir.is_dir():
        return
    exclude = git_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    line = ".cz/"
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if line not in text.splitlines():
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
        exclude.write_text(text, encoding="utf-8")


def apply_pointers(
    project: Path,
    *,
    skip_pointers: bool = False,
    hermes_memory: bool = False,
    assume_yes: bool = False,
) -> list[str]:
    """Install pointer files; returns list of relative paths touched."""
    if skip_pointers:
        return []
    touched: list[str] = []
    targets = [
        ("AGENTS.md", AGENTS_BLOCK),
        ("CLAUDE.md", CLAUDE_BLOCK),
    ]
    for rel, block in targets:
        path = project / rel
        if is_git_tracked(project, rel) and not assume_yes:
            raise RuntimeError(
                f"{rel} is tracked by git; re-run with --yes after reviewing the pointer block"
            )
        if _insert_or_replace(path, block):
            touched.append(rel)

    rule_path = project / ".cursor" / "rules" / "cz-home.mdc"
    if _insert_or_replace(rule_path, CURSOR_RULE_BODY):
        touched.append(str(rule_path.relative_to(project)))

    if hermes_memory:
        mem = Path.home() / ".hermes" / "MEMORY.md"
        if mem.exists():
            text = mem.read_text(encoding="utf-8")
            if HERMES_MEMORY_LINE not in text:
                if len(text) + len(HERMES_MEMORY_LINE) + 2 > 2200:
                    pass  # skip silently per char limit
                else:
                    mem.write_text(text.rstrip() + "\n" + HERMES_MEMORY_LINE + "\n", encoding="utf-8")
                    touched.append("~/.hermes/MEMORY.md (append)")

    return touched


def remove_pointers(project: Path) -> list[str]:
    removed: list[str] = []
    for rel in ("AGENTS.md", "CLAUDE.md"):
        if _remove_block(project / rel):
            removed.append(rel)
    rule = project / ".cursor" / "rules" / "cz-home.mdc"
    if rule.exists() and _remove_block(rule):
        removed.append(str(rule.relative_to(project)))
    return removed
