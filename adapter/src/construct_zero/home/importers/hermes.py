"""Hermes session importer (best effort)."""

from __future__ import annotations

from pathlib import Path

from construct_zero.home.checkpoint import Checkpoint


def from_session(project: Path) -> Checkpoint:
    cp = Checkpoint(from_agent="hermes", reason="quota")
    # Hermes session layout varies by version; checkpoint file is primary.
    cp.next_step = "Run `./construct-zero chat` and read `.cz/checkpoint.md`."
    _ = project
    return cp
