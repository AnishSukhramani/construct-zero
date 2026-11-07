"""Agent ignore file scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest
from construct_zero.security.agent_ignore import ensure_agent_ignore_files


def test_writes_cursorignore_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install = tmp_path / "app" / "construct-zero"
    project = tmp_path / "app"
    install.mkdir(parents=True)
    (project / ".git").mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    touched = ensure_agent_ignore_files(project)
    assert ".cursorignore" in touched
    text = (project / ".cursorignore").read_text(encoding="utf-8")
    assert "construct-zero/" in text
    assert ensure_agent_ignore_files(project) == []
