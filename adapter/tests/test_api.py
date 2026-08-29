"""Unit tests that do not require CURSOR_API_KEY."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from hcx.config import HCXConfig, load_config
from hcx.core.backend import CompletionResult, HealthStatus, StreamChunk
from hcx.core.sessions import SessionStore, ToolLoopSession
from hcx.drivers.claude_code import ClaudeCodeDriver
from hcx.openai_types import ChatCompletionRequest, ChatMessage
from hcx.server import create_app


class FakeBackend:
    name = "cursor"

    def health(self) -> HealthStatus:
        return HealthStatus(ok=True, detail="fake ok")

    def list_models(self) -> list[str]:
        return ["auto", "composer-2.5"]

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        if request.tools:
            return CompletionResult(
                tool_calls=[
                    {
                        "id": "call_test1",
                        "type": "function",
                        "function": {
                            "name": "terminal",
                            "arguments": json.dumps({"command": "echo hi"}),
                        },
                    }
                ],
                finish_reason="tool_calls",
                model=request.model or "auto",
            )
        last = request.messages[-1].content if request.messages else ""
        return CompletionResult(text=f"echo:{last}", model=request.model or "auto")

    def stream(self, request: ChatCompletionRequest):
        result = self.complete(request)
        yield StreamChunk(
            data={
                "id": "chatcmpl-x",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": result.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": result.text or ""},
                        "finish_reason": None,
                    }
                ],
            }
        )
        yield StreamChunk(
            data={
                "id": "chatcmpl-x",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": result.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
            done=True,
        )


def test_load_example_config():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    cfg = load_config(root / "config" / "hermesxcursor.yaml.example")
    assert cfg.adapter.host == "127.0.0.1"
    assert cfg.adapter.port == 8765
    assert cfg.inference.backend == "cursor"
    assert cfg.inference.model == "auto"
    assert cfg.inference.cursor.mode == "ask"


def test_tool_loop_session_park_and_deliver():
    store = SessionStore()
    session = store.create()
    pending = session.park("terminal", '{"command":"echo hi"}', call_id="call_abc")
    assert pending.call_id == "call_abc"
    assert session.deliver_result("call_abc", '{"ok":true}')
    assert session.wait_result("call_abc", timeout=1.0) == '{"ok":true}'


def test_claude_code_stub():
    drv = ClaudeCodeDriver()
    assert drv.health().ok is False
    try:
        drv.complete(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="hi")])
        )
        assert False, "expected NotImplementedError"
    except NotImplementedError:
        pass


def test_health_and_models_and_chat(monkeypatch):
    cfg = HCXConfig()
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    client = TestClient(app)

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"

    m = client.get("/v1/models")
    assert m.status_code == 200
    ids = [x["id"] for x in m.json()["data"]]
    assert "auto" in ids

    c = client.post(
        "/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "PONG"}],
        },
    )
    assert c.status_code == 200
    body = c.json()
    assert body["choices"][0]["message"]["content"].startswith("echo:")


def test_tool_calls_response_shape():
    cfg = HCXConfig()
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    client = TestClient(app)

    c = client.post(
        "/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "run something"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "description": "run shell",
                        "parameters": {
                            "type": "object",
                            "properties": {"command": {"type": "string"}},
                        },
                    },
                }
            ],
        },
    )
    assert c.status_code == 200
    msg = c.json()["choices"][0]["message"]
    assert msg["tool_calls"][0]["function"]["name"] == "terminal"
    assert c.json()["choices"][0]["finish_reason"] == "tool_calls"


def test_auth_bearer():
    cfg = HCXConfig()
    cfg.adapter.api_key = "secret"
    app = create_app(cfg)
    app.state.backend = FakeBackend()
    client = TestClient(app)

    assert client.get("/v1/models").status_code == 401
    assert (
        client.get("/v1/models", headers={"Authorization": "Bearer secret"}).status_code
        == 200
    )
