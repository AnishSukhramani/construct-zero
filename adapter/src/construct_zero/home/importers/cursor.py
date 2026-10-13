"""Cursor importer — checkpoint file + git diff."""

from __future__ import annotations

import subprocess
from pathlib import Path

from construct_zero.home.checkpoint import Checkpoint, parse_checkpoint
from construct_zero.home.store import CzStore


def from_project(project: Path) -> Checkpoint:
    cp = Checkpoint(from_agent="cursor", reason="quota")
    store = CzStore(project)
    path = store.root / "checkpoint.md"
    if path.exists():
        parsed = parse_checkpoint(path.read_text(encoding="utf-8"))
        if parsed:
            return parsed
    try:
        diff = subprocess.run(
            ["git", "-C", str(project), "diff", "--stat"],
            capture_output=True,
            text=True,
            check=False,
        )
        cp.files_touched = (diff.stdout or "").strip()
    except OSError:
        pass
    cp.next_step = "Read `.cz/checkpoint.md` and continue."
    return cp
