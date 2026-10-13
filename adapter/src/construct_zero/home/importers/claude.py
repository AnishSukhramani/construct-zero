"""Claude Code jsonl importer (best effort)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from construct_zero.home.checkpoint import Checkpoint
from construct_zero.home.redact import wrap_imported


def _encoded_cwd(project: Path) -> str:
    return base64.urlsafe_b64encode(str(project.resolve()).encode()).decode().rstrip("=")


def from_transcript(project: Path) -> Checkpoint:
    base = Path.home() / ".claude" / "projects" / _encoded_cwd(project)
    cp = Checkpoint(from_agent="claude-code", reason="quota")
    if not base.is_dir():
        return cp
    files = sorted(base.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return cp
    last_user = ""
    last_assistant = ""
    todos = ""
    last_err = ""
    for line in files[0].read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = row.get("role") or row.get("type")
        content = row.get("content") or row.get("message") or ""
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
            )
        text = str(content)[:4000]
        if role in ("user", "human"):
            last_user = text
        elif role in ("assistant", "message"):
            last_assistant = text
        if "todo" in text.lower():
            todos = text
        if row.get("is_error") or "error" in str(row.get("level", "")).lower():
            last_err = text
    cp.goal = wrap_imported(last_user, "claude-code") if last_user else ""
    cp.in_progress = wrap_imported(todos or last_assistant, "claude-code")
    cp.next_step = "Continue from in-progress work in checkpoint."
    cp.last_error = wrap_imported(last_err, "claude-code") if last_err else ""
    return cp
