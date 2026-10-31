"""CI: no embedded telemetry in Construct-Zero runtime packages."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_telemetry_markers() -> None:
    script = ROOT / "scripts" / "ci" / "telemetry_check.py"
    proc = subprocess.run(
        ["python3", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
