"""Shared pytest hooks for adapter tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Prefer fake cursor_sdk before any construct_zero driver import.
_FAKE = Path(__file__).resolve().parent / "fake_cursor_sdk.py"
if "cursor_sdk" not in sys.modules:
    import importlib.util

    spec = importlib.util.spec_from_file_location("cursor_sdk", _FAKE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cursor_sdk"] = mod
    spec.loader.exec_module(mod)


@pytest.fixture(autouse=True)
def _reset_fake_cursor_sdk() -> None:
    import cursor_sdk

    cursor_sdk.Agent.reset()
