"""Track wrapped child processes for construct-zero kill."""

from __future__ import annotations

import os
import signal
import subprocess
import time

_pids: set[int] = set()


def register_pid(pid: int) -> None:
    _pids.add(pid)


def unregister_pid(pid: int) -> None:
    _pids.discard(pid)


def terminate_all(timeout: float = 1.5) -> None:
    targets = list(_pids)
    for pid in targets:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
    deadline = time.time() + timeout
    while time.time() < deadline and targets:
        alive = []
        for pid in targets:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except OSError:
                unregister_pid(pid)
        targets = alive
        if targets:
            time.sleep(0.05)
    for pid in targets:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        unregister_pid(pid)


def spawn_tracked(cmd: list[str], **kwargs) -> subprocess.Popen:
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        **kwargs,
    )
    register_pid(proc.pid)
    return proc
