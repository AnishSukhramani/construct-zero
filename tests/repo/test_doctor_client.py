"""Doctor --client=cline and default output compatibility."""

from __future__ import annotations

import os
import re
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SNAP = Path(__file__).resolve().parent / "snapshots"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def mock_adapter_env() -> dict[str, str]:
    port = _free_port()
    env = {
        **os.environ,
        "CZ_ROOT": str(ROOT),
        "CZ_BACKEND": "mock",
        "CZ_PORT": str(port),
        "CZ_DOCTOR_SKIP_HERMES": "1",
        "CZ_DOCTOR_CHAT": "1",
        "PYTHONPATH": str(ROOT / "adapter" / "src"),
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
        env=env,
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
        pytest.fail("adapter did not start")
    yield env
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _normalize_doctor_output(text: str) -> str:
    text = re.sub(r"127\.0\.0\.1:\d+", "127.0.0.1:PORT", text)
    text = re.sub(r"CZ_PORT=\d+", "CZ_PORT=PORT", text)
    text = re.sub(r'"created":\s*\d+', '"created": 0', text)
    text = re.sub(r"/home/[^/\s]+/", "$HOME/", text)
    return text


def _run_doctor(extra: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), *extra],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_doctor_default_matches_snapshot(mock_adapter_env: dict[str, str]) -> None:
    snap_path = SNAP / "doctor_default_ok.txt"
    proc = _run_doctor([], mock_adapter_env)
    combined = _normalize_doctor_output(proc.stdout + proc.stderr)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    expected = snap_path.read_text()
    assert combined == expected
    assert proc.returncode == 0


def test_doctor_cline_passes(mock_adapter_env: dict[str, str]) -> None:
    proc = _run_doctor(["--client=cline"], mock_adapter_env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Paste into Cline" in proc.stdout
    assert "C3 Cline-shaped text request OK" in proc.stdout


def test_doctor_cline_skips_chat(mock_adapter_env: dict[str, str]) -> None:
    env = {**mock_adapter_env, "CZ_DOCTOR_CHAT": "0"}
    proc = _run_doctor(["--client=cline"], env)
    assert "C3/C4 skipped" in proc.stdout


def test_doctor_unsupported_clients_exit_zero(mock_adapter_env: dict[str, str]) -> None:
    for client in ("aider", "openhands"):
        proc = _run_doctor([f"--client={client}"], mock_adapter_env)
        assert proc.returncode == 0
        assert "Not yet supported" in proc.stdout


def test_doctor_unknown_client_exit_two(mock_adapter_env: dict[str, str]) -> None:
    proc = _run_doctor(["--client=unknown-client"], mock_adapter_env)
    assert proc.returncode == 2


def test_doctor_cline_wrong_model_fails(mock_adapter_env: dict[str, str]) -> None:
    proc = _run_doctor(["--client=cline", "--model=no-such-model-xyz"], mock_adapter_env)
    assert proc.returncode == 1
    assert "FAIL C2" in proc.stderr or "FAIL C2" in proc.stdout
