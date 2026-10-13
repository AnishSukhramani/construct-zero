"""Backend registry and routing."""

from __future__ import annotations

import pytest
from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.core.registry import build, parse_routed_model, resolve
from construct_zero.core.sessions import SessionStore
from construct_zero.drivers.claude_code import ClaudeCodeDriver
from construct_zero.drivers.cursor import CursorDriver
from construct_zero.drivers.mock import MockDriver
from construct_zero.server import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("cursor", "cursor"),
        ("hcx", "cursor"),
        ("construct-zero", "cursor"),
        ("cz", "cursor"),
        ("mock", "mock"),
        ("claude_code", "claude_code"),
        ("claude-code", "claude_code"),
        ("claude", "claude_code"),
    ],
)
def test_resolve_aliases(alias: str, expected: str) -> None:
    assert resolve(alias) == expected


def test_unknown_backend_lists_valid() -> None:
    with pytest.raises(ValueError, match="Valid:"):
        resolve("not-a-backend")


def test_build_returns_expected_classes() -> None:
    sessions = SessionStore()
    cfg = CZConfig()
    assert isinstance(build(cfg, sessions, "cursor"), CursorDriver)
    assert isinstance(build(cfg, sessions, "mock"), MockDriver)
    assert isinstance(build(cfg, sessions, "claude_code"), ClaudeCodeDriver)


def test_health_includes_capabilities() -> None:
    client = TestClient(create_app(CZConfig(inference=InferenceConfig(backend="mock"))))
    body = client.get("/health").json()
    assert body["capabilities"]["tools"] is True
    assert "backends_available" in body
    assert "mock" in body["backends_available"]


def test_claude_code_tools_501() -> None:
    cfg = CZConfig(inference=InferenceConfig(backend="claude_code"))
    client = TestClient(create_app(cfg))
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function", "function": {"name": "t", "parameters": {}}}],
        },
    )
    assert r.status_code == 501
    assert "not supported" in r.json()["error"]["message"].lower()


def test_routing_off_unchanged_model() -> None:
    assert parse_routed_model("auto") == (None, "auto")
    cfg = CZConfig(inference=InferenceConfig(backend="mock", routing=False))
    client = TestClient(create_app(cfg))
    r = client.post(
        "/v1/chat/completions",
        json={"model": "mock:auto", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 200
    assert "mock:" in (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "")


def test_routing_on_prefixed_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "fake")
    cfg = CZConfig(inference=InferenceConfig(backend="mock", routing=True))
    client = TestClient(create_app(cfg))
    listed = [m["id"] for m in client.get("/v1/models").json()["data"]]
    assert "cursor:auto" in listed
    r = client.post(
        "/v1/chat/completions",
        json={"model": "mock:mock-model", "messages": [{"role": "user", "content": "routed"}]},
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"].startswith("mock:routed")


def test_build_import_error_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    import construct_zero.core.registry as reg

    reg._register_builtins()

    def boom(cfg, sessions):
        raise ImportError("no extra")

    spec = reg._BACKENDS["cursor"]
    monkeypatch.setitem(reg._BACKENDS, "cursor", reg.BackendSpec(
        name="cursor",
        factory=boom,
        capabilities=spec.capabilities,
    ))
    b = reg.build(CZConfig(inference=InferenceConfig(backend="cursor")), SessionStore())
    assert b.health().ok is False
    assert "Install" in b.health().detail or "extra" in b.health().detail.lower()


def test_image_warning_header() -> None:
    client = TestClient(create_app(CZConfig(inference=InferenceConfig(backend="mock"))))
    r = client.post(
        "/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "hi"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                    ],
                }
            ],
        },
    )
    assert r.status_code == 200
    assert r.headers.get("X-CZ-Warning") == "images-dropped"
