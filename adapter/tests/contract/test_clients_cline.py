"""Cline-shaped requests against mock and fake-cursor backends."""

from __future__ import annotations

import json
from pathlib import Path

from contract_util import validate
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "clients" / "cline"


def test_cline_text_fixture(mock_client: TestClient) -> None:
    body = json.loads((FIXTURES / "request.json").read_text())
    r = mock_client.post("/v1/chat/completions", json=body)
    assert r.status_code == 200, r.text
    validate(r.json(), "chat_completion.json")


def test_cline_streaming(mock_client: TestClient) -> None:
    body = {
        "model": "auto",
        "messages": [{"role": "user", "content": "stream test"}],
        "stream": True,
    }
    with mock_client.stream("POST", "/v1/chat/completions", json=body) as resp:
        assert resp.status_code == 200
        chunks = list(resp.iter_lines())
    assert any(b"data:" in (c.encode() if isinstance(c, str) else c) for c in chunks)
    assert any(b"[DONE]" in (c.encode() if isinstance(c, str) else c) for c in chunks)


def test_cline_tool_round_trip(mock_client: TestClient) -> None:
    tool_req = {
        "model": "auto",
        "messages": [{"role": "user", "content": "read something"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
                },
            }
        ],
    }
    r1 = mock_client.post("/v1/chat/completions", json=tool_req)
    assert r1.status_code == 200
    tc = r1.json()["choices"][0]["message"].get("tool_calls")
    assert tc
    call_id = tc[0]["id"]
    r2 = mock_client.post(
        "/v1/chat/completions",
        json={
            "model": "auto",
            "messages": [
                {"role": "user", "content": "read something"},
                {"role": "assistant", "content": None, "tool_calls": tc},
                {"role": "tool", "tool_call_id": call_id, "content": "file contents"},
            ],
        },
    )
    assert r2.status_code == 200
    validate(r2.json(), "chat_completion.json")
