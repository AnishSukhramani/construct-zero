"""audit-ignore.toml expiry logic."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = ROOT / "scripts" / "ci" / "audit_ignore_check.py"
    spec = importlib.util.spec_from_file_location("audit_ignore_check", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["audit_ignore_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_expired_ignore_fails(tmp_path: Path, monkeypatch) -> None:
    mod = _load()
    p = tmp_path / "audit-ignore.toml"
    past = (date.today() - timedelta(days=1)).isoformat()
    p.write_text(
        f'[[ignore]]\nid = "CVE-9999-TEST"\nreason = "test"\nexpires = "{past}"\n'
    )
    monkeypatch.setattr(mod, "PATH", p)
    assert mod.main() == 1


def test_future_ignore_ok(tmp_path: Path, monkeypatch) -> None:
    mod = _load()
    p = tmp_path / "audit-ignore.toml"
    future = (date.today() + timedelta(days=30)).isoformat()
    p.write_text(
        f'[[ignore]]\nid = "CVE-9999-TEST"\nreason = "test"\nexpires = "{future}"\n'
    )
    monkeypatch.setattr(mod, "PATH", p)
    assert mod.main() == 0
