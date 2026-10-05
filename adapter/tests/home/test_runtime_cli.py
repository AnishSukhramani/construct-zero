"""CLI coverage for run, handoff, kill, unkill, usage."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from construct_zero.home import ledger as cz_ledger
from construct_zero.home.runtime_cli import cmd_kill, cmd_run, main


def _fake_dir() -> str:
    return str(Path(__file__).parent / "fake_agents")


def test_runtime_run_and_handoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_HOME_FAKE_AGENTS_DIR", _fake_dir())
    monkeypatch.setenv("CZ_RUN_NO_PTY", "1")
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    rc = main(["run", "cursor", "--", "hello"])
    assert rc == 0
    rc = main(["handoff", "--to", "hermes", "--no-launch", "--from-agent", "claude"])
    assert rc == 0


def test_runtime_kill_unkill_usage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    db = tmp_path / "usage.db"
    cz_ledger.init_db(db)
    cz_ledger.record_usage(
        agent="a1",
        session="s1",
        model="auto",
        prompt_tokens=10,
        completion_tokens=5,
        request_id="r1",
        status=200,
        db_path=db,
    )
    monkeypatch.setattr(
        "construct_zero.home.runtime_cli.cz_ledger.aggregate_usage",
        lambda **kwargs: [{"key": "a1", "total_tokens": 15, "requests": 1}],
    )
    assert main(["usage", "--json"]) == 0
    assert main(["usage"]) == 0

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    monkeypatch.setattr("construct_zero.home.runtime_cli.httpx.post", lambda *a, **k: mock_resp)
    assert main(["kill", "--reason", "test"]) == 0
    assert main(["unkill"]) == 0


def test_cmd_kill_local_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        "construct_zero.home.runtime_cli.httpx.post",
        lambda *a, **k: (_ for _ in ()).throw(httpx.HTTPError("offline")),
    )
    from construct_zero.home.runtime_cli import cmd_unkill

    assert cmd_kill(type("A", (), {"reason": "x"})()) == 0
    assert cmd_unkill() == 0


def test_cmd_run_runtime_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CZ_HOME_FAKE_AGENTS_DIR", "/nonexistent")
    monkeypatch.setenv("CZ_RUN_NO_PTY", "1")
    args = type(
        "A", (), {"agent": "claude", "agent_args": [], "auto_handoff": False, "no_pty": True}
    )()
    assert cmd_run(args) == 2
    assert "agent not found" in capsys.readouterr().err
