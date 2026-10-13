"""Editable/path lines are stripped before pip-audit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = ROOT / "scripts" / "ci" / "filter_audit_requirements.py"
    spec = importlib.util.spec_from_file_location("filter_audit_requirements", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["filter_audit_requirements"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_strips_editable_and_file_url_lines() -> None:
    mod = _load()
    raw = """-e ../vpl
    # via construct-zero-voice
requests==2.32.0 \\
    --hash=sha256:abc
"""
    out = mod.filter_requirements(raw)
    assert "-e" not in out
    assert "requests==2.32.0" in out
    assert "sha256:abc" in out
