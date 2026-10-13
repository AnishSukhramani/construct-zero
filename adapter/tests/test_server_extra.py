"""Extra server routes for coverage."""

from __future__ import annotations

from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


def test_streaming_image_warning_header():
    client = TestClient(create_app(CZConfig(inference=InferenceConfig(backend="mock"))))
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "auto",
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": "http://x"}}],
                }
            ],
        },
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers.get("X-CZ-Warning") == "images-dropped"
