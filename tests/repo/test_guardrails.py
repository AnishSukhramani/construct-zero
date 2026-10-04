"""Unit tests for scripts/ci/guardrails.py rules."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "ci" / "guardrails.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("guardrails", GUARD)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _mini_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("base\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    return tmp_path


def test_src_without_tests_fails(tmp_path: Path) -> None:
    g = _load_guard()
    repo = _mini_repo(tmp_path)
    p = repo / "adapter" / "src" / "construct_zero" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("x = 1\n")
    subprocess.run(["git", "add", "adapter/src/construct_zero/x.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "src"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
    errs = g.check(base=base, labels=set(), pr_body="", local=True, repo_root=repo)
    assert any("without test" in e for e in errs)


def test_src_without_tests_passes_with_label(tmp_path: Path) -> None:
    g = _load_guard()
    repo = _mini_repo(tmp_path)
    p = repo / "adapter" / "src" / "construct_zero" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("x = 1\n")
    subprocess.run(["git", "add", "adapter/src/construct_zero/x.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "src"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
    errs = g.check(base=base, labels={"no-test-needed"}, pr_body="", local=True, repo_root=repo)
    assert not any("without test" in e for e in errs)


def test_deleted_test_fails_without_label(tmp_path: Path) -> None:
    g = _load_guard()
    repo = _mini_repo(tmp_path)
    t = repo / "adapter" / "tests" / "test_x.py"
    t.parent.mkdir(parents=True)
    t.write_text("def test_x(): pass\n")
    subprocess.run(["git", "add", "adapter/tests/test_x.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "add test"], cwd=repo, check=True)
    t.unlink()
    subprocess.run(["git", "add", "adapter/tests/test_x.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "del test"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
    errs = g.check(base=base, labels=set(), pr_body="", local=True, repo_root=repo)
    assert any("test-change-approved" in e for e in errs)


def test_protected_path_requires_body_section(tmp_path: Path) -> None:
    g = _load_guard()
    repo = _mini_repo(tmp_path)
    mf = repo / "Makefile"
    mf.write_text("ci:\n\ttrue\n")
    subprocess.run(["git", "add", "Makefile"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "mk"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
    errs = g.check(base=base, labels=set(), pr_body="", local=False, repo_root=repo)
    assert any("Protected paths" in e for e in errs)


def test_protected_path_with_body_ok(tmp_path: Path) -> None:
    g = _load_guard()
    repo = _mini_repo(tmp_path)
    mf = repo / "Makefile"
    mf.write_text("ci:\n\ttrue\n")
    subprocess.run(["git", "add", "Makefile"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "mk"], cwd=repo, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=repo, text=True).strip()
    body = "## Protected paths\n\n- `Makefile` — local CI entrypoint\n"
    errs = g.check(base=base, labels=set(), pr_body=body, local=False, repo_root=repo)
    assert not errs
