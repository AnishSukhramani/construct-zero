from __future__ import annotations

import os
import subprocess
from pathlib import Path

from construct_zero.home.checkpoint import parse_checkpoint
from construct_zero.home.runner import handoff_to, run_agent


def _fake_dir() -> str:
    return str(Path(__file__).parent / "fake_agents")


def test_run_quota_auto_handoff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CZ_HOME_FAKE_AGENTS_DIR", _fake_dir())
    monkeypatch.setenv("CZ_RUN_NO_PTY", "1")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    result = run_agent("claude", [], project=tmp_path, auto_handoff=True, use_pty=False)
    assert result.quota_hit
    assert result.handoff_to == "cursor"
    cp = parse_checkpoint((tmp_path / ".cz" / "checkpoint.md").read_text(encoding="utf-8"))
    assert cp is not None
    assert cp.reason == "quota"
    assert list((tmp_path / ".cz" / "handoffs").glob("*.md"))


def test_handoff_no_launch_prints_command(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("CZ_HOME_FAKE_AGENTS_DIR", _fake_dir())
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    cmd = handoff_to("hermes", project=tmp_path, launch=False, from_agent="claude-code")
    assert "fake_hermes" in cmd or "hermes" in cmd
    assert "-q" in cmd
