"""env_cz precedence and deprecation warnings."""

from __future__ import annotations

import warnings

import construct_zero.envcompat as envcompat
from construct_zero.envcompat import env_cz


def test_cz_takes_precedence(monkeypatch):
    monkeypatch.setenv("CZ_MODEL", "from-cz")
    monkeypatch.setenv("HCX_MODEL", "from-hcx")
    assert env_cz("MODEL") == "from-cz"


def test_hcx_fallback_warns_once(monkeypatch):
    envcompat._warned.clear()
    monkeypatch.delenv("CZ_HOST", raising=False)
    monkeypatch.setenv("HCX_HOST", "legacy")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert env_cz("HOST") == "legacy"
        assert env_cz("HOST") == "legacy"
    assert len([w for w in caught if issubclass(w.category, DeprecationWarning)]) == 1


def test_default_when_unset(monkeypatch):
    monkeypatch.delenv("CZ_FOO", raising=False)
    monkeypatch.delenv("HCX_FOO", raising=False)
    assert env_cz("FOO", default="d") == "d"
