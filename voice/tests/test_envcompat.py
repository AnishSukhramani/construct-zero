"""Voice envcompat parity tests."""

from __future__ import annotations

from construct_zero_voice.envcompat import env_cz


def test_voice_env_cz_precedence(monkeypatch):
    monkeypatch.setenv("CZ_HEALTH_URL", "http://127.0.0.1:1/health")
    monkeypatch.setenv("HCX_HEALTH_URL", "http://legacy/health")
    assert env_cz("HEALTH_URL") == "http://127.0.0.1:1/health"
