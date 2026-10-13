"""Hermes bridge helpers without subprocess or network."""

from __future__ import annotations

from unittest.mock import MagicMock

import construct_zero_voice.hermes_bridge as bridge


def test_repo_root_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CZ_REPO_ROOT", str(tmp_path))
    assert bridge.repo_root() == tmp_path


def test_check_adapter_up_ok(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok"}
    monkeypatch.setattr(bridge.httpx, "get", lambda *a, **k: mock_resp)
    ok, detail = bridge.check_adapter_up()
    assert ok is True
    assert detail == "ok"


def test_check_adapter_up_unreachable(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(bridge.httpx, "get", boom)
    ok, detail = bridge.check_adapter_up()
    assert ok is False
    assert "unreachable" in detail
