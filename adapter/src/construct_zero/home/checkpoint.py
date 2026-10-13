"""Checkpoint schema read/write for `.cz/checkpoint.md`."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from construct_zero.home.redact import redact
from construct_zero.home.store import CzStore, atomic_write

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

SECTIONS = [
    "Goal",
    "Done",
    "In progress (exact state)",
    "Next step (first action for the next agent)",
    "Files touched",
    "Last error / blockers",
    "Do not",
]


@dataclass
class Checkpoint:
    from_agent: str
    reason: str
    goal: str = ""
    done: str = ""
    in_progress: str = ""
    next_step: str = ""
    files_touched: str = ""
    last_error: str = ""
    do_not: str = ""
    repo_head: str = ""
    dirty_files: list[str] = field(default_factory=list)
    created: str = ""

    def to_markdown(self) -> str:
        created = self.created or datetime.now(timezone.utc).astimezone().isoformat(
            timespec="seconds"
        )
        meta = {
            "cz_checkpoint": 1,
            "from_agent": self.from_agent,
            "created": created,
            "reason": self.reason,
            "repo_head": self.repo_head or "(unknown)",
            "dirty_files": self.dirty_files,
        }
        body_parts = []
        for title, val in [
            ("Goal", self.goal),
            ("Done", self.done),
            ("In progress (exact state)", self.in_progress),
            ("Next step (first action for the next agent)", self.next_step),
            ("Files touched", self.files_touched),
            ("Last error / blockers", self.last_error),
            ("Do not", self.do_not),
        ]:
            body_parts.append(f"## {title}\n{val.strip()}\n")
        front = yaml.safe_dump(meta, sort_keys=False).strip()
        return f"---\n{front}\n---\n" + "\n".join(body_parts)


def parse_checkpoint(text: str) -> Checkpoint | None:
    m = FRONT_RE.match(text)
    if not m:
        return None
    meta = yaml.safe_load(m.group(1)) or {}
    if meta.get("cz_checkpoint") != 1:
        return None
    body = text[m.end() :]
    sections = {s: "" for s in SECTIONS}
    for sec in SECTIONS:
        pat = re.compile(
            rf"##\s+{re.escape(sec)}\s*\n(.*?)(?=##\s+|\Z)",
            re.DOTALL,
        )
        sm = pat.search(body)
        if sm:
            sections[sec] = sm.group(1).strip()
    return Checkpoint(
        from_agent=str(meta.get("from_agent", "")),
        reason=str(meta.get("reason", "")),
        created=str(meta.get("created", "")),
        repo_head=str(meta.get("repo_head", "")),
        dirty_files=list(meta.get("dirty_files") or []),
        goal=sections["Goal"],
        done=sections["Done"],
        in_progress=sections["In progress (exact state)"],
        next_step=sections["Next step (first action for the next agent)"],
        files_touched=sections["Files touched"],
        last_error=sections["Last error / blockers"],
        do_not=sections["Do not"],
    )


def git_snapshot(project: Path) -> tuple[str, list[str]]:
    try:
        head = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        repo_head = (head.stdout or "").strip() or "(none)"
        diff = subprocess.run(
            ["git", "-C", str(project), "diff", "--stat"],
            capture_output=True,
            text=True,
            check=False,
        )
        dirty = []
        for line in (diff.stdout or "").splitlines():
            if "|" in line and not line.startswith(" "):
                dirty.append(line.split("|", 1)[0].strip())
        return repo_head, dirty
    except OSError:
        return "(none)", []


def handoff_prompt(from_agent: str) -> str:
    return (
        f"You are continuing work handed off from {from_agent}. "
        "Read .cz/checkpoint.md and .cz/CONTEXT.md. "
        "Start with 'Next step'. Do not redo 'Done'."
    )


def write_checkpoint(project: Path, cp: Checkpoint, *, archive: bool = True) -> Path:
    store = CzStore(project)
    store.init_scaffold()
    text = redact(cp.to_markdown())
    path = store.root / "checkpoint.md"
    from construct_zero.home.lockfile import cz_file_lock

    with cz_file_lock(store.lock_path):
        atomic_write(path, text)
        if archive:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            name = f"{ts}-{cp.from_agent}-handoff.md"
            handoff_dir = store.root / "handoffs"
            handoff_dir.mkdir(parents=True, exist_ok=True)
            atomic_write(handoff_dir / name, text)
    return path
