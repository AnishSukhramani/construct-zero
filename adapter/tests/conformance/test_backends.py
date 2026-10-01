"""Backend conformance — mock must pass; claude_code strict xfail."""

from __future__ import annotations

import pytest
from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "backend",
    ["mock"],
)
def test_backend_health_and_chat(backend: str) -> None:
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
    cfg = CZConfig(inference=InferenceConfig(backend="claude_code"))
    client = TestClient(create_app(cfg))
    r = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert r.status_code in {501, 502}
