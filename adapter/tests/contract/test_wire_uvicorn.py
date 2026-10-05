"""Wire-level contract against a real uvicorn listener (ephemeral port)."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from contract_util import validate

ROOT = Path(__file__).resolve().parents[3]
ADAPTER = ROOT / "adapter"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def contract_base_url() -> str:
    env = os.environ.get("CZ_CONTRACT_BASE_URL", "").strip()
    if env:
        yield env.rstrip("/")
        return

    port = _free_port()
    env_vars = {
        **os.environ,
        "CZ_BACKEND": "mock",
        "PYTHONPATH": str(ADAPTER / "src"),
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
        cwd=ADAPTER,
        env=env_vars,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base}/health", timeout=1.0)
            if r.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("uvicorn contract server did not become ready")
    try:
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_wire_health_and_chat(contract_base_url: str) -> None:
    with httpx.Client(base_url=contract_base_url, timeout=10.0) as client:
        health = client.get("/health").json()
        validate(health, "health.json")
        chat = client.post(
            "/v1/chat/completions",
            json={"model": "auto", "messages": [{"role": "user", "content": "wire"}]},
        )
        assert chat.status_code == 200
        validate(chat.json(), "chat_completion.json")
