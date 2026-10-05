"""CLI coverage for construct-zero home subcommands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from construct_zero.home.cli import main as home_main


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "cz-state"))
    return tmp_path


def test_home_init_status_sync_agents_memory(project: Path) -> None:
    assert home_main(["init", "--no-pointers"]) == 0
    assert home_main(["init", "--no-pointers"]) == 0
    assert home_main(["status"]) == 0
    assert home_main(["sync"]) == 0
    assert home_main(["agents"]) == 0
    token_rc = home_main(["agents", "key", "test-agent"])
    assert token_rc == 0
    assert home_main(["memory", "add", "Title", "Body text"]) == 0
    assert home_main(["memory", "list"]) == 0
    assert home_main(["memory", "list", "--all"]) == 0


def test_home_memory_supersede_expire(project: Path) -> None:
    home_main(["init", "--no-pointers"])
    eid = _memory_add_id(project)
    assert home_main(["memory", "supersede", eid, "New title", "New body"]) == 0
    assert home_main(["memory", "expire", eid]) == 0


def _memory_add_id(project: Path) -> str:
    from construct_zero.home.store import CzStore

    return CzStore(project).memory_add("T", "B")


def test_home_uninstall_and_init_with_pointers(project: Path) -> None:
    (project / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    assert home_main(["init", "--yes"]) == 0
    assert "<!-- cz:home:start -->" in (project / "AGENTS.md").read_text(encoding="utf-8")
    assert home_main(["uninstall"]) == 0


def test_home_agents_key_missing_id(project: Path) -> None:
    home_main(["init", "--no-pointers"])
    with pytest.raises(SystemExit) as exc:
        home_main(["agents", "key"])
    assert exc.value.code == 2


def test_home_status_json_shape(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home_main(["init", "--no-pointers"])
    capsys.readouterr()
    home_main(["status"])
    data = json.loads(capsys.readouterr().out)
    assert "store" in data
    assert "registry_agents" in data
