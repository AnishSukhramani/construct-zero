"""Stable CLI --help and example config load snapshots."""

from __future__ import annotations

import subprocess
from pathlib import Path

from construct_zero.config import load_config

ROOT = Path(__file__).resolve().parents[2]


def test_load_example_config() -> None:
    cfg = load_config(ROOT / "config" / "construct-zero.yaml.example")
    assert cfg.adapter.host == "127.0.0.1"
    assert cfg.adapter.port == 8765
    assert cfg.inference.backend == "cursor"


def _help(script: str) -> str:
    r = subprocess.run(
        ["bash", str(ROOT / script), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return (r.stdout or "") + (r.stderr or "")


def test_construct_zero_help_menu() -> None:
    text = subprocess.run(
        [str(ROOT / "construct-zero"), "help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "start" in text
    assert "doctor" in text


def test_install_and_setup_help() -> None:
    assert "Usage" in _help("install.sh") or "usage" in _help("install.sh").lower()
    assert "--skip-hermes" in _help("scripts/setup.sh")
