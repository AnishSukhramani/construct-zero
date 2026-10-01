"""Per-project `.cz/` shared context store."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from construct_zero.home.lockfile import cz_file_lock
from construct_zero.home.paths import project_cz_dir

MEMORY_HEADING_RE = re.compile(
    r"^##\s+(M-\d{8}-\d{4})\s+·\s+(.+)$", re.MULTILINE
)
ENTRY_ID_RE = re.compile(r"^M-\d{8}-\d{4}$")

DEFAULT_CONTEXT = """# Project context

Brief goal, stack, and conventions for all agents working in this repo.
Edit freely; agents should read this before starting work.
"""

DEFAULT_MEMORY = """# Shared memory

Durable facts with provenance. Use `construct-zero home memory add` or append entries:

```markdown
## M-YYYYMMDD-NNNN · Title
- status: active
- by: agent · ISO8601 · session …
- supersedes: (none)
- expires: (none)
Body text here.
```
"""

DEFAULT_DECISIONS = """# Decisions log

Append-only ADR-lite entries.
"""

DEFAULT_TASKS = """# Tasks

| Task | Owner | Status |
|------|-------|--------|
"""

DEFAULT_CHECKPOINT = """---
cz_checkpoint: 1
from_agent: (none)
created: (none)
reason: (none)
repo_head: (none)
dirty_files: []
---
## Goal

## Done

## In progress (exact state)

## Next step (first action for the next agent)

## Files touched

## Last error / blockers

## Do not

"""


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


@dataclass
class MemoryEntry:
    entry_id: str
    title: str
    body: str
    content_hash: str


def _entry_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _parse_memory_entries(text: str) -> dict[str, MemoryEntry]:
    entries: dict[str, MemoryEntry] = {}
    parts = re.split(r"(?=^## M-\d{8}-\d{4})", text, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part.startswith("## M-"):
            continue
        m = MEMORY_HEADING_RE.match(part.split("\n", 1)[0])
        if not m:
            continue
        eid, title = m.group(1), m.group(2).strip()
        entries[eid] = MemoryEntry(
            entry_id=eid,
            title=title,
            body=part,
            content_hash=_entry_hash(part),
        )
    return entries


def _next_memory_id(existing: Iterable[str]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"M-{today}-"
    nums = []
    for eid in existing:
        if eid.startswith(prefix):
            try:
                nums.append(int(eid.split("-")[-1]))
            except ValueError:
                pass
    n = max(nums, default=0) + 1
    return f"{prefix}{n:04d}"


class CzStore:
    def __init__(self, project: Path | None = None) -> None:
        self.project = (project or Path.cwd()).resolve()
        self.root = project_cz_dir(self.project)
        self.lock_path = self.root / ".lock"

    def exists(self) -> bool:
        return self.root.is_dir()

    def init_scaffold(self) -> list[str]:
        """Create `.cz/` tree; return list of paths created (empty if already present)."""
        created: list[str] = []
        with cz_file_lock(self.lock_path):
            specs = {
                "CONTEXT.md": DEFAULT_CONTEXT,
                "MEMORY.md": DEFAULT_MEMORY,
                "DECISIONS.md": DEFAULT_DECISIONS,
                "TASKS.md": DEFAULT_TASKS,
                "checkpoint.md": DEFAULT_CHECKPOINT,
            }
            for name, default in specs.items():
                path = self.root / name
                if not path.exists():
                    atomic_write(path, default)
                    created.append(str(path.relative_to(self.project)))
            for sub in ("handoffs", "channel"):
                d = self.root / sub
                if not d.exists():
                    d.mkdir(parents=True, exist_ok=True)
                    created.append(str(d.relative_to(self.project)) + "/")
        return created

    def read_memory(self) -> str:
        path = self.root / "MEMORY.md"
        if not path.exists():
            return DEFAULT_MEMORY
        return path.read_text(encoding="utf-8")

    def write_memory(self, text: str, *, expected_hashes: dict[str, str] | None = None) -> list[str]:
        """Write MEMORY.md; on hash conflict append to MEMORY.conflicts.md. Returns warnings."""
        warnings: list[str] = []
        with cz_file_lock(self.lock_path):
            current = self.read_memory()
            if expected_hashes:
                current_entries = _parse_memory_entries(current)
                for eid, exp in expected_hashes.items():
                    cur = current_entries.get(eid)
                    if cur and cur.content_hash != exp:
                        conflict_path = self.root / "MEMORY.conflicts.md"
                        block = cur.body + "\n\n---\n\n"
                        if conflict_path.exists():
                            block = conflict_path.read_text(encoding="utf-8") + "\n" + block
                        atomic_write(conflict_path, block)
                        warnings.append(
                            f"Memory entry {eid} changed concurrently; copy saved to MEMORY.conflicts.md"
                        )
            atomic_write(self.root / "MEMORY.md", text)
        return warnings

    def memory_add(
        self,
        title: str,
        body: str,
        *,
        by: str = "user",
        session: str = "cli",
    ) -> str:
        text = self.read_memory()
        entries = _parse_memory_entries(text)
        eid = _next_memory_id(entries.keys())
        ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        block = (
            f"## {eid} · {title}\n"
            f"- status: active\n"
            f"- by: {by} · {ts} · session {session}\n"
            f"- supersedes: (none)\n"
            f"- expires: (none)\n"
            f"{body.strip()}\n"
        )
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
        self.write_memory(text)
        return eid

    def memory_supersede(self, entry_id: str, new_title: str, new_body: str, *, by: str = "user") -> str:
        if not ENTRY_ID_RE.match(entry_id):
            raise ValueError(f"invalid memory id: {entry_id}")
        text = self.read_memory()
        entries = _parse_memory_entries(text)
        old = entries.get(entry_id)
        if not old:
            raise KeyError(entry_id)
        old_body = re.sub(
            r"(- status:\s*)active",
            r"\1superseded",
            old.body,
            count=1,
        )
        text = text.replace(old.body, old_body)
        entries = _parse_memory_entries(text)
        eid = _next_memory_id(entries.keys())
        ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        block = (
            f"## {eid} · {new_title}\n"
            f"- status: active\n"
            f"- by: {by} · {ts} · session cli\n"
            f"- supersedes: {entry_id}\n"
            f"- expires: (none)\n"
            f"{new_body.strip()}\n"
        )
        if not text.endswith("\n"):
            text += "\n"
        text += "\n" + block
        self.write_memory(text)
        return eid

    def memory_expire(self, entry_id: str) -> None:
        text = self.read_memory()
        entries = _parse_memory_entries(text)
        old = entries.get(entry_id)
        if not old:
            raise KeyError(entry_id)
        new_body = re.sub(
            r"(- status:\s*)\w+",
            r"\1expired",
            old.body,
            count=1,
        )
        text = text.replace(old.body, new_body)
        self.write_memory(text)

    def memory_list(self, *, include_all: bool = False) -> list[MemoryEntry]:
        entries = _parse_memory_entries(self.read_memory())
        out = list(entries.values())
        if not include_all:
            out = [
                e
                for e in out
                if "status: active" in e.body or "status:active" in e.body.replace(" ", "")
            ]
        return sorted(out, key=lambda e: e.entry_id)

    def status_summary(self) -> dict:
        mem = self.memory_list(include_all=True)
        agent_written = sum(1 for e in mem if "- by:" in e.body and "user" not in e.body.split("- by:")[1][:20])
        return {
            "project": str(self.project),
            "cz_dir": str(self.root),
            "initialized": self.exists(),
            "memory_entries": len(mem),
            "agent_written_memory": agent_written,
        }
