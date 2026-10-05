"""First-run / doctor error message snapshots with fix hints."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAP = Path(__file__).resolve().parent / "snapshots"


def _base_env(**extra: str) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "CZ_ROOT": str(ROOT),
    }
    env.update(extra)
    return env


def _snap(name: str) -> str:
    return (SNAP / name).read_text()


def test_install_sh_documents_non_empty_folder() -> None:
    text = (ROOT / "install.sh").read_text()
    assert "not empty" in text.lower() or "not empty" in text


def test_doctor_missing_cursor_key_message() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=_base_env(CZ_BACKEND="cursor", CURSOR_API_KEY=""),
    )
    blob = (r.stdout or "") + (r.stderr or "")
    for line in _snap("doctor_missing_cursor_key.txt").strip().splitlines():
        assert line.strip() in blob


def test_doctor_adapter_down_message() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=_base_env(
            CZ_BACKEND="mock",
            CZ_DOCTOR_SKIP_HERMES="1",
            CURSOR_API_KEY="unused",
        ),
    )
    blob = (r.stdout or "") + (r.stderr or "")
    for line in _snap("doctor_adapter_down.txt").strip().splitlines():
        assert line.strip() in blob


def test_start_port_busy_preflight_message() -> None:
    """Port-busy preflight emits actionable text (see start_port_busy snapshot)."""
    text = (ROOT / "scripts" / "start-adapter.sh").read_text()
    snap = _snap("start_port_busy.txt")
    for line in snap.strip().splitlines():
        assert line.strip() in text
