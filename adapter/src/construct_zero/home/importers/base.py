"""Route importer by agent id."""

from __future__ import annotations

from pathlib import Path

from construct_zero.home.checkpoint import Checkpoint, git_snapshot, parse_checkpoint
from construct_zero.home.importers import claude as claude_imp
from construct_zero.home.importers import cursor as cursor_imp
from construct_zero.home.importers import hermes as hermes_imp
from construct_zero.home.store import CzStore


def import_checkpoint(project: Path, agent_id: str, *, reason: str = "quota") -> Checkpoint:
    store = CzStore(project)
    existing = None
    cp_path = store.root / "checkpoint.md"
    if cp_path.exists():
        existing = parse_checkpoint(cp_path.read_text(encoding="utf-8"))
    head, dirty = git_snapshot(project)
    if agent_id == "claude-code":
        partial = claude_imp.from_transcript(project)
    elif agent_id == "hermes":
        partial = hermes_imp.from_session(project)
    else:
        partial = cursor_imp.from_project(project)
    if existing and existing.next_step:
        partial.next_step = existing.next_step or partial.next_step
    partial.from_agent = agent_id
    partial.reason = reason
    partial.repo_head = head
    partial.dirty_files = dirty
    return partial
