"""Hermes compat at the pinned ref (runs in hermes-pinned CI with HERMES_PIN_ROOT)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

PIN = os.environ.get("HERMES_PIN_ROOT", "")
pytestmark = pytest.mark.skipif(not PIN, reason="Set HERMES_PIN_ROOT (hermes-pinned CI job)")


def test_hermes_source_present() -> None:
    root = Path(PIN)
    assert (root / "pyproject.toml").is_file() or (root / "setup.py").is_file()


def test_construct_zero_plugin_yaml_exists() -> None:
    plugin = Path(__file__).resolve().parents[2] / "hermes-plugin/model-providers/construct-zero/plugin.yaml"
    assert plugin.is_file()
    text = plugin.read_text()
    assert "construct-zero" in text
