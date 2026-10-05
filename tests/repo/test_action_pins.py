"""GitHub Action SHA pins must match tagged releases."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_action_pins_format_and_remote() -> None:
    script = ROOT / "scripts" / "ci" / "verify-action-pins.py"
    subprocess.run(["python3", str(script), "--offline"], cwd=ROOT, check=True)
    subprocess.run(["python3", str(script)], cwd=ROOT, check=True, timeout=120)
