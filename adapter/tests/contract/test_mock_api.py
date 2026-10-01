"""Contract smoke tests against the mock backend (in-process)."""

from __future__ import annotations

from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    cfg = CZConfig(inference=InferenceConfig(backend="mock"))
    return TestClient(create_app(cfg))


def test_health_mock() -> None:
    r = _client().get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["backend"] == "mock"


def test_chat_completion_mock() -> None:
    r = _client().post(
        "/v1/chat/completions",
        json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    assert "mock:hi" in r.json()["choices"][0]["message"]["content"]


def test_auth_envelope() -> None:
    cfg = CZConfig()
    cfg.adapter.api_key = "secret"
    cfg.inference.backend = "mock"
    client = TestClient(create_app(cfg))
    r = client.post(
        "/v1/chat/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["detail"]
    assert body["error"]["code"] == "cz_auth_missing"
