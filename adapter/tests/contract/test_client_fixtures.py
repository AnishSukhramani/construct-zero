"""Replay recorded client request shapes against the mock backend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contract_util import validate

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "clients"


def _client_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


@pytest.mark.parametrize("client_dir", _client_dirs(), ids=lambda p: p.name)
def test_client_fixture_replay(client_dir: Path, mock_client: TestClient) -> None:
    meta = json.loads((client_dir / "metadata.json").read_text())
    body = json.loads((client_dir / "request.json").read_text())
    path = meta.get("base_path", "/v1/chat/completions")
    r = mock_client.post(path, json=body)
    assert r.status_code == 200, r.text
    validate(r.json(), "chat_completion.json")
