"""Exercise scripts/ci/verify-staged.sh against temporary git repos."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "ci" / "verify-staged.sh"


def _run_verify(cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [str(VERIFY)],
        cwd=cwd,
        env=e,
        text=True,
        capture_output=True,
    )


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("ok\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.mark.parametrize(
    "rel_path",
    [
        "hermes/x",
        ".hermes/x",
        ".construct-zero/x",
        ".venvs/x",
        "adapter/.venv/x",
        ".env",
        ".env.local",
        "private/x",
        "zzz-docs/x",
        "config/construct-zero.yaml",
        "config/hermesxcursor.yaml",
        "foo.log",
        ".claude/x",
    ],
)
def test_forbidden_staged_path_blocked(mini_repo: Path, rel_path: str) -> None:
    target = mini_repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x\n")
    subprocess.run(["git", "add", "-f", rel_path], cwd=mini_repo, check=True)
    r = _run_verify(mini_repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert rel_path.split("/")[0] in r.stderr or rel_path in r.stderr


def test_env_example_allowed(mini_repo: Path) -> None:
    (mini_repo / ".env.example").write_text("CURSOR_API_KEY=unused\n")
    subprocess.run(["git", "add", ".env.example"], cwd=mini_repo, check=True)
    r = _run_verify(mini_repo)
    assert r.returncode == 0, r.stderr


def test_secret_in_added_lines_blocked(mini_repo: Path) -> None:
    p = mini_repo / "leak.txt"
    p.write_text("CURSOR_API_KEY=sk-real-secret-value\n")
    subprocess.run(["git", "add", "leak.txt"], cwd=mini_repo, check=True)
    r = _run_verify(mini_repo)
    assert r.returncode == 1
    assert "CURSOR_API_KEY" in r.stderr


def test_unused_placeholder_allowed(mini_repo: Path) -> None:
    p = mini_repo / "ok.txt"
    p.write_text("CURSOR_API_KEY=unused\n")
    subprocess.run(["git", "add", "ok.txt"], cwd=mini_repo, check=True)
    r = _run_verify(mini_repo)
    assert r.returncode == 0, r.stderr


def test_clean_staging_passes(mini_repo: Path) -> None:
    p = mini_repo / "adapter" / "src" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("x = 1\n")
    subprocess.run(["git", "add", "adapter/src/x.py"], cwd=mini_repo, check=True)
    r = _run_verify(mini_repo)
    assert r.returncode == 0, r.stderr
