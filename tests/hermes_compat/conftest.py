"""Hermes pinned-source fixtures (hermes-pinned CI sets HERMES_PIN_ROOT)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def hermes_pin_root() -> Path:
    pin = os.environ.get("HERMES_PIN_ROOT", "").strip()
    if not pin:
        pytest.skip("Set HERMES_PIN_ROOT (hermes-pinned CI job)")
    root = Path(pin)
    if not root.is_dir():
        pytest.skip(f"HERMES_PIN_ROOT not a directory: {pin}")
    return root


@pytest.fixture(scope="session")
def hermes_pin_env(hermes_pin_root: Path) -> Path:
    """Install construct-zero user plugin and expose Hermes on sys.path."""
    base = os.environ.get("RUNNER_TEMP", "/tmp")
    home = Path(os.environ.get("HERMES_HOME", f"{base}/hermes-home-ci"))
    home.mkdir(parents=True, exist_ok=True)
    plugin_dest = home / "plugins" / "model-providers" / "construct-zero"
    plugin_dest.parent.mkdir(parents=True, exist_ok=True)
    src = ROOT / "hermes-plugin" / "model-providers" / "construct-zero"
    if plugin_dest.is_symlink() or plugin_dest.exists():
        plugin_dest.unlink()
    plugin_dest.symlink_to(src, target_is_directory=True)
    os.environ["HERMES_HOME"] = str(home)
    pin_str = str(hermes_pin_root)
    if pin_str not in sys.path:
        sys.path.insert(0, pin_str)
    return hermes_pin_root
