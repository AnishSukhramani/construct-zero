"""PTY-backed agent runner with quota detection and handoff."""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import termios
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from construct_zero.home.checkpoint import handoff_prompt, write_checkpoint
from construct_zero.home.importers.base import import_checkpoint
from construct_zero.home.quota import match_quota
from construct_zero.home import registry as reg_mod

AGENT_ALIASES = {
    "claude": "claude-code",
    "cursor": "cursor",
    "hermes": "hermes",
}


def normalize_agent(name: str) -> str:
    return AGENT_ALIASES.get(name, name)


def resolve_bin(agent_id: str) -> list[str]:
    fake_root = os.environ.get("CZ_HOME_FAKE_AGENTS_DIR", "").strip()
    if fake_root:
        mapping = {
            "claude-code": "fake_claude.py",
            "cursor": "fake_cursor.py",
            "hermes": "fake_hermes.py",
        }
        script = mapping.get(agent_id)
        if script:
            path = Path(fake_root) / script
            if path.is_file():
                return [sys.executable, str(path)]
    reg = reg_mod.sync_registry()
    for a in reg.agents:
        if a.id == agent_id:
            if agent_id == "hermes":
                return [a.bin, "chat"]
            return [a.bin]
    raise RuntimeError(f"agent not found: {agent_id}")


def next_fallback(current: str) -> str | None:
    reg = reg_mod.load_registry()
    order = reg.fallback_order or reg_mod.DEFAULT_FALLBACK
    try:
        idx = order.index(current)
    except ValueError:
        return None
    if idx + 1 < len(order):
        return order[idx + 1]
    return None


@dataclass
class RunResult:
    exit_code: int
    quota_hit: bool
    handoff_to: str | None = None


def run_agent(
    agent_id: str,
    args: list[str],
    *,
    project: Path | None = None,
    auto_handoff: bool = False,
    on_quota: Callable[[], None] | None = None,
    use_pty: bool | None = None,
) -> RunResult:
    agent_id = normalize_agent(agent_id)
    project = (project or Path.cwd()).resolve()
    cmd = resolve_bin(agent_id) + args
    if use_pty is None:
        use_pty = os.environ.get("CZ_RUN_NO_PTY", "") != "1" and sys.stdin.isatty()

    collected: list[str] = []
    quota = False

    def _handle_quota() -> None:
        nonlocal quota
        quota = True
        cp = import_checkpoint(project, agent_id, reason="quota")
        write_checkpoint(project, cp)
        if on_quota:
            on_quota()

    if not use_pty:
        proc = subprocess.run(
            cmd,
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        collected.append(out)
        sys.stdout.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        if match_quota(agent_id, out):
            _handle_quota()
        handoff = None
        if quota and auto_handoff:
            nxt = next_fallback(agent_id)
            if nxt:
                handoff = nxt
                _launch_handoff(nxt, agent_id, project)
        return RunResult(proc.returncode, quota, handoff)

    master, slave = pty.openpty()
    proc = subprocess.Popen(
        cmd,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=project,
        close_fds=True,
    )
    os.close(slave)
    try:
        old = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
    except (termios.error, OSError):
        old = None
    try:
        while True:
            r, _, _ = select.select([master, sys.stdin], [], [], 0.2)
            if master in r:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    break
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                collected.append(text)
                os.write(sys.stdout.fileno(), data)
                if match_quota(agent_id, "".join(collected)):
                    _handle_quota()
                    if auto_handoff:
                        nxt = next_fallback(agent_id)
                        if nxt:
                            proc.terminate()
                            _launch_handoff(nxt, agent_id, project)
                            return RunResult(0, True, nxt)
                    break
            if sys.stdin in r:
                try:
                    data = os.read(sys.stdin.fileno(), 4096)
                except OSError:
                    break
                if not data:
                    break
                os.write(master, data)
            if proc.poll() is not None:
                break
        code = proc.wait(timeout=5)
    finally:
        if old is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        os.close(master)
    out = "".join(collected)
    if not quota and match_quota(agent_id, out):
        _handle_quota()
    handoff = None
    if quota and auto_handoff:
        handoff = next_fallback(agent_id)
        if handoff:
            _launch_handoff(handoff, agent_id, project)
    return RunResult(code, quota, handoff)


def _launch_handoff(to_agent: str, from_agent: str, project: Path) -> None:
    prompt = handoff_prompt(from_agent)
    agent_id = normalize_agent(to_agent)
    cmd = resolve_bin(agent_id)
    if agent_id == "hermes":
        cmd += ["-q", prompt]
    else:
        cmd += ["-p", prompt]
    subprocess.Popen(cmd, cwd=project)


def handoff_to(
    agent_id: str,
    *,
    project: Path | None = None,
    reason: str = "manual",
    launch: bool = True,
    from_agent: str = "manual",
) -> str:
    project = (project or Path.cwd()).resolve()
    agent_id = normalize_agent(agent_id)
    cp = import_checkpoint(project, from_agent, reason=reason)
    cp.from_agent = from_agent
    cp.reason = reason
    write_checkpoint(project, cp)
    cmd_parts = resolve_bin(agent_id)
    prompt = handoff_prompt(from_agent)
    if agent_id == "hermes":
        continue_cmd = " ".join(cmd_parts + ["-q", repr(prompt)])
    else:
        continue_cmd = " ".join(cmd_parts + ["-p", repr(prompt)])
    if launch:
        if agent_id == "hermes":
            subprocess.Popen(cmd_parts + ["-q", prompt], cwd=project)
        else:
            subprocess.Popen(cmd_parts + ["-p", prompt], cwd=project)
    return continue_cmd
