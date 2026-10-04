from __future__ import annotations

import subprocess
import time
from pathlib import Path

import yaml
from construct_zero.config import CZConfig
from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.home import admin as cz_admin
from construct_zero.home import kill_registry as cz_kill_registry
from construct_zero.home.ledger import assert_schema_no_content_columns, init_db
from construct_zero.openai_types import ChatCompletionRequest
from construct_zero.server import create_app
from fastapi.testclient import TestClient


class FakeBackend:
    name = "cursor"

    def health(self) -> HealthStatus:
        return HealthStatus(ok=True, detail="fake")

    def list_models(self) -> list[str]:
        return ["auto"]

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        last = request.messages[-1].content if request.messages else ""
        return CompletionResult(text=f"echo:{last}", model="auto")

    def stream(self, request: ChatCompletionRequest):
        result = self.complete(request)
        yield StreamChunk(
            data={
                "choices": [{"delta": {"content": result.text}, "finish_reason": None}],
            }
        )
        yield StreamChunk(data={"choices": [{"delta": {}, "finish_reason": "stop"}]}, done=True)


def test_schema_no_content_columns(tmp_path: Path) -> None:
    db = tmp_path / "usage.db"
    assert_schema_no_content_columns(db)


def test_chat_unchanged_without_budgets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    cfg = CZConfig()
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    app.state.cz_ledger_path = tmp_path / "usage.db"
    app.state.cz_budgets_path = tmp_path / "no-budgets.yaml"
    client = TestClient(app)
    r = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "PONG"}]},
    )
    assert r.status_code == 200


def test_budget_429(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    budgets = tmp_path / "budgets.yaml"
    budgets.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "enforce": True,
                "defaults": {"per_session_tokens": 10},
                "agents": {},
            }
        )
    )
    db = tmp_path / "usage.db"
    init_db(db)
    cfg = CZConfig()
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    app.state.cz_ledger_path = db
    app.state.cz_budgets_path = budgets
    client = TestClient(app)
    headers = {"X-CZ-Agent": "claude-code", "X-CZ-Session": "sess1"}
    r = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "x" * 400}],
        },
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "cz_budget_exceeded"


def test_kill_503_and_admin_auth(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path / "state"))
    cfg = CZConfig()
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    app.state.cz_ledger_path = tmp_path / "usage.db"
    client = TestClient(app)
    admin = cz_admin.ensure_admin_key()
    assert client.get("/cz/v1/usage").status_code == 401
    assert (
        client.get("/cz/v1/usage", headers={"Authorization": f"Bearer {admin}"}).status_code == 200
    )
    client.post("/cz/v1/admin/kill", headers={"Authorization": f"Bearer {admin}"})
    r = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "cz_killed"
    client.post("/cz/v1/admin/unkill", headers={"Authorization": f"Bearer {admin}"})
    r2 = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r2.status_code == 200


def test_kill_terminates_children_within_2s() -> None:
    proc = subprocess.Popen(
        ["sleep", "30"],
        start_new_session=True,
    )
    cz_kill_registry.register_pid(proc.pid)
    start = time.time()
    cz_kill_registry.terminate_all(timeout=1.5)
    elapsed = time.time() - start
    assert elapsed < 2.0
    assert proc.poll() is not None
