"""Agent registry at $CZ_STATE_DIR/home/registry.json."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from construct_zero.home.paths import cz_root, cz_state_dir

REGISTRY_VERSION = 1
DEFAULT_FALLBACK = ["claude-code", "cursor", "hermes"]


@dataclass
class AgentRecord:
    id: str
    bin: str
    detected: str
    version: str = ""
    headless: bool = False
    via_cz: bool = False


@dataclass
class ProjectRecord:
    path: str
    initialized: str
    pointers: list[str] = field(default_factory=list)


@dataclass
class Registry:
    version: int = REGISTRY_VERSION
    agents: list[AgentRecord] = field(default_factory=list)
    projects: list[ProjectRecord] = field(default_factory=list)
    fallback_order: list[str] = field(default_factory=lambda: list(DEFAULT_FALLBACK))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "agents": [asdict(a) for a in self.agents],
            "projects": [asdict(p) for p in self.projects],
            "fallback_order": self.fallback_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Registry:
        agents = [AgentRecord(**a) for a in data.get("agents", [])]
        projects = [ProjectRecord(**p) for p in data.get("projects", [])]
        return cls(
            version=int(data.get("version", REGISTRY_VERSION)),
            agents=agents,
            projects=projects,
            fallback_order=list(data.get("fallback_order", DEFAULT_FALLBACK)),
        )


def registry_path() -> Path:
    return cz_state_dir() / "home" / "registry.json"


def load_registry() -> Registry:
    path = registry_path()
    if not path.exists():
        return Registry()
    return Registry.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_registry(reg: Registry) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg.to_dict(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _version_of(cmd: str) -> str:
    try:
        out = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        line = (out.stdout or out.stderr or "").strip().split("\n", 1)[0]
        return line[:120]
    except (OSError, subprocess.TimeoutExpired):
        return ""


def detect_agents() -> list[AgentRecord]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    found: list[AgentRecord] = []

    claude = _which("claude")
    if claude:
        found.append(
            AgentRecord(
                id="claude-code",
                bin=claude,
                detected=now,
                version=_version_of(claude),
                headless=True,
            )
        )

    cursor = _which("cursor-agent")
    if cursor:
        found.append(
            AgentRecord(
                id="cursor",
                bin=cursor,
                detected=now,
                version=_version_of(cursor),
                headless=True,
            )
        )

    root = cz_root()
    hermes_bin = None
    if root:
        candidate = root / ".venvs" / "hermes" / "bin" / "hermes"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            hermes_bin = str(candidate)
    if not hermes_bin:
        hermes_bin = _which("hermes")
    if hermes_bin:
        found.append(
            AgentRecord(
                id="hermes",
                bin=hermes_bin,
                detected=now,
                version=_version_of(hermes_bin),
                headless=False,
                via_cz=True,
            )
        )

    return found


def sync_registry() -> Registry:
    reg = load_registry()
    reg.agents = detect_agents()
    if not reg.fallback_order:
        reg.fallback_order = list(DEFAULT_FALLBACK)
    save_registry(reg)
    return reg


def register_project(project: Path, pointers: list[str]) -> None:
    reg = load_registry()
    path = str(project.resolve())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    reg.projects = [p for p in reg.projects if p.path != path]
    reg.projects.append(ProjectRecord(path=path, initialized=now, pointers=list(pointers)))
    save_registry(reg)
