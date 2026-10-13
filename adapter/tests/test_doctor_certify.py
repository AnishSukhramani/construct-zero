"""CZ Certified doctor profile."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def mock_adapter() -> dict[str, str]:
    port = _free_port()
    env = {
        **os.environ,
        "CZ_ROOT": str(ROOT),
        "CZ_BACKEND": "mock",
        "CZ_PORT": str(port),
        "CZ_DOCTOR_SKIP_HERMES": "1",
        "CZ_DOCTOR_CERTIFY_OFFLINE": "1",
    }
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "-m",
            "uvicorn",
            "construct_zero.server:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ROOT / "adapter",
        env={**env, "PYTHONPATH": str(ROOT / "adapter" / "src")},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            import urllib.request

            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("adapter not up")
    yield env
    proc.terminate()


def test_certify_offline_json_schema(mock_adapter: dict[str, str]) -> None:
    env = {**mock_adapter, "CZ_DOCTOR_CERTIFY_OFFLINE": "1"}
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "construct_zero.doctor.cli",
            "--certify",
            "--json",
            "--offline",
        ],
        cwd=ROOT / "adapter",
        env={**env, "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    from contract_util import validate

    validate(data, "doctor.json")
    assert data["certified"] is True
    assert "sk-" not in proc.stdout


def test_certify_table_verdict(mock_adapter: dict[str, str]) -> None:
    env = {**mock_adapter, "CZ_DOCTOR_CERTIFY_OFFLINE": "1"}
    proc = subprocess.run(
        ["uv", "run", "python", "-m", "construct_zero.doctor.cli", "--certify", "--offline"],
        cwd=ROOT / "adapter",
        env={**env, "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "CERTIFIED (cz-certified-v1)" in proc.stdout
