"""Backend conformance — mock must pass; claude_code strict xfail."""

from __future__ import annotations

import pytest
from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize("backend", ["mock", "cursor"])
def test_backend_health_and_chat(backend: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if backend == "cursor":
        monkeypatch.setenv("CURSOR_API_KEY", "fake-key-for-tests")
    cfg = CZConfig(inference=InferenceConfig(backend=backend))
    client = TestClient(create_app(cfg))
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"
    c = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert c.status_code == 200


@pytest.mark.xfail(strict=True, reason="claude_code stub until PR 15")
def test_claude_code_not_conformant_yet() -> None:
    pytest.fail("claude_code backend is not conformant yet")
