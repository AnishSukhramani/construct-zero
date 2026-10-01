"""Validate mock/cursor responses against JSON Schemas."""

from __future__ import annotations

import json

import pytest
from contract_util import validate
from fastapi.testclient import TestClient


def test_schema_health(mock_client: TestClient) -> None:
    body = mock_client.get("/health").json()
    validate(body, "health.json")


def test_schema_models_list(mock_client: TestClient) -> None:
    body = mock_client.get("/v1/models").json()
    validate(body, "models_list.json")


def test_schema_chat_completion(mock_client: TestClient) -> None:
    r = mock_client.post(
        "/v1/chat/completions",
        json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    validate(r.json(), "chat_completion.json")


def test_schema_error_envelope(mock_client: TestClient) -> None:
    from construct_zero.config import CZConfig, InferenceConfig
    from construct_zero.server import create_app

    cfg = CZConfig(inference=InferenceConfig(backend="mock"))
    cfg.adapter.api_key = "secret"
    client = TestClient(create_app(cfg))
    r = client.post(
        "/v1/chat/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401
    validate(r.json(), "error.json")


def test_schema_stream_chunks(mock_client: TestClient) -> None:
    with mock_client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "stream": True,
            "messages": [{"role": "user", "content": "stream-me"}],
        },
    ) as resp:
        assert resp.status_code == 200
        saw_data = False
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line.removeprefix("data: ").strip()
            if payload == "[DONE]":
                break
            saw_data = True
            validate(json.loads(payload), "chat_completion_chunk.json")
        assert saw_data


def test_extra_request_fields_ignored(mock_client: TestClient) -> None:
    r = mock_client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "x"}],
            "client_fixture_tag": "ignored-by-server",
            "unknown_openai_field": 123,
        },
    )
    assert r.status_code == 200
    validate(r.json(), "chat_completion.json")


@pytest.mark.parametrize("client_fixture", ["mock_client", "cursor_client"])
def test_cursor_and_mock_chat_schema(
    client_fixture: str, request: pytest.FixtureRequest
) -> None:
    client: TestClient = request.getfixturevalue(client_fixture)
    r = client.post(
        "/v1/chat/completions",
        json={"model": "auto", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert r.status_code == 200
    validate(r.json(), "chat_completion.json")
