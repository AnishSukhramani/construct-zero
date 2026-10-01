"""Exercise scripts/run-tests.sh exit codes."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "scripts" / "run-tests.sh"


def test_run_tests_fast_exits_zero() -> None:
    env = os.environ.copy()
    env["PATH"] = f"{os.environ.get('HOME', '')}/.local/bin:" + env.get("PATH", "")
    env["CZ_RUN_TESTS_NESTED"] = "1"  # avoid re-entering repo tests from run-tests.sh
    r = subprocess.run(
        [str(RUN), "--fast"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_run_tests_reports_failing_package() -> None:
    env = os.environ.copy()
    env["PATH"] = f"{os.environ.get('HOME', '')}/.local/bin:" + env.get("PATH", "")
    env["CZ_RUN_TESTS_FAIL_PKG"] = "adapter"
    env["CZ_RUN_TESTS_NESTED"] = "1"
    r = subprocess.run(
        [str(RUN), "--fast"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert r.returncode != 0
    assert "adapter" in r.stderr or "adapter" in r.stdout
