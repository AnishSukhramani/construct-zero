"""VPL envcompat tests."""

from __future__ import annotations

from construct_zero_vpl.envcompat import env_cz


def test_vpl_env_default(monkeypatch):
    monkeypatch.delenv("CZ_BAR", raising=False)
    monkeypatch.delenv("HCX_BAR", raising=False)
    assert env_cz("BAR") is None
