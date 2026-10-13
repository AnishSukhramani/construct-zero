"""pin_bump_check no-op when lock unchanged."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = ROOT / "scripts" / "ci" / "pin_bump_check.py"
    spec = importlib.util.spec_from_file_location("pin_bump_check", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["pin_bump_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_pin_bump_noop_on_push(monkeypatch) -> None:
    mod = _load()
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    assert mod.main() == 0
