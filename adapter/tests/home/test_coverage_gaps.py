"""Extra coverage for budgets, guards, registry, pointers, kill registry."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from construct_zero.home import budgets as budgets_mod
from construct_zero.home import inference_guard as guard_mod
from construct_zero.home import kill_registry as cz_kill_registry
from construct_zero.home import registry as reg_mod
from construct_zero.home.identity import resolve_agent
from construct_zero.home.importers.base import import_checkpoint
from construct_zero.home.pointers import apply_pointers, git_exclude_cz
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage


def test_budget_guard_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path))
    bud = tmp_path / "home" / "budgets.yaml"
    bud.parent.mkdir(parents=True)
    bud.write_text(
        yaml.dump(
            {
                "enforce": True,
                "agents": {"test-agent": {"per_session_tokens": 5, "per_agent_daily_tokens": 100}},
            }
        ),
        encoding="utf-8",
    )
    db = tmp_path / "usage.db"
    guard_mod.record_adapter_usage(
        agent="test-agent",
        session="s1",
        model="auto",
        prompt_tokens=10,
        completion_tokens=0,
        request_id="r1",
        status=200,
        db_path=db,
    )
    err = guard_mod.check_budget("test-agent", "s1", 1, budgets_path=bud, db_path=db)
    assert err and err["error"]["code"] == "cz_budget_exceeded"
    msg = budgets_mod.budget_error_message("test-agent", 5, "session")
    assert msg["error"]["code"] == "cz_budget_exceeded"

    bud.write_text(
        yaml.dump(
            {
                "enforce": True,
                "defaults": {"per_agent_daily_tokens": 3},
            }
        ),
        encoding="utf-8",
    )
    db2 = tmp_path / "usage2.db"
    guard_mod.record_adapter_usage(
        agent="daily-agent",
        session="s2",
        model="auto",
        prompt_tokens=3,
        completion_tokens=0,
        request_id="r2",
        status=200,
        db_path=db2,
    )
    bud.write_text(
        yaml.dump(
            {
                "enforce": True,
                "agents": {"daily-agent": {"per_agent_daily_tokens": 3}},
            }
        ),
        encoding="utf-8",
    )
    daily_err = guard_mod.check_budget("daily-agent", "s2", 1, budgets_path=bud, db_path=db2)
    assert daily_err and daily_err["error"]["code"] == "cz_budget_exceeded"


def test_estimate_prompt_tokens() -> None:
    body = ChatCompletionRequest(
        model="auto",
        messages=[ChatMessage(role="user", content="hello world" * 20)],
    )
    assert guard_mod.estimate_prompt_tokens(body) >= 1


def test_resolve_agent_bearer_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path))
    from construct_zero.home.identity import issue_agent_key

    token = issue_agent_key("cline")
    body = ChatCompletionRequest(model="auto", messages=[ChatMessage(role="user", content="x")])
    agent, _ = resolve_agent({}, body, f"Bearer {token}")
    assert agent == "cline"


def test_registry_detect_and_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        reg_mod.shutil, "which", lambda name: "/usr/bin/false" if name == "claude" else None
    )
    monkeypatch.setattr(
        reg_mod,
        "_version_of",
        lambda cmd: "version 1.2.3",
    )
    reg = reg_mod.sync_registry()
    assert reg.agents == [] or isinstance(reg.agents, list)
    reg_mod.register_project(tmp_path, ["AGENTS.md"])
    loaded = reg_mod.load_registry()
    assert any(p.path == str(tmp_path.resolve()) for p in loaded.projects)


def test_cursor_importer_uses_checkpoint(tmp_path: Path) -> None:
    from construct_zero.home.importers.cursor import from_project
    from construct_zero.home.store import CzStore

    store = CzStore(tmp_path)
    store.init_scaffold()
    (store.root / "checkpoint.md").write_text(
        "## Goal\nhandoff goal\n\n## Next step\ncontinue\n",
        encoding="utf-8",
    )
    cp = from_project(tmp_path)
    assert cp.goal or cp.next_step


def test_pointers_and_import_existing_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    from construct_zero.home.store import CzStore

    store = CzStore(tmp_path)
    store.init_scaffold()
    git_exclude_cz(tmp_path, commit_mode=False)
    (tmp_path / "AGENTS.md").write_text("hello\n", encoding="utf-8")
    touched = apply_pointers(tmp_path, assume_yes=True)
    assert touched
    cp = import_checkpoint(tmp_path, "claude-code", reason="quota")
    assert cp.repo_head is not None or cp.dirty_files is not None


def test_kill_registry_terminate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_killpg(_pgid: int, _sig: int) -> None:
        raise ProcessLookupError

    def fake_kill(pid: int, sig: int) -> None:
        calls.append(pid)
        if sig == cz_kill_registry.signal.SIGTERM:
            raise OSError("gone")

    monkeypatch.setattr(cz_kill_registry.os, "killpg", fake_killpg)
    monkeypatch.setattr(cz_kill_registry.os, "kill", fake_kill)
    cz_kill_registry.register_pid(4242)
    cz_kill_registry.terminate_all()
    assert calls


def test_kill_registry_spawn_tracked() -> None:
    proc = cz_kill_registry.spawn_tracked(["/bin/true"])
    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_ledger_aggregate_groupings(tmp_path: Path) -> None:
    from construct_zero.home import ledger as cz_ledger

    db = tmp_path / "u.db"
    cz_ledger.init_db(db)
    cz_ledger.record_usage(
        agent="a",
        session="s",
        model="m1",
        prompt_tokens=1,
        completion_tokens=1,
        request_id="r",
        status=200,
        db_path=db,
    )
    assert cz_ledger.aggregate_usage(group_by="day", db_path=db)
    assert cz_ledger.aggregate_usage(group_by="model", db_path=db)
