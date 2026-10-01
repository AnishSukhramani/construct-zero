"""Ensure export-ignore paths are omitted from git archive."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

IGNORED_PREFIXES = (
    ".github/",
    "tests/",
    "adapter/tests/",
    "scripts/ci/",
    "Makefile",
)


def test_gitattributes_declares_export_ignore() -> None:
    text = (ROOT / ".gitattributes").read_text()
    for prefix in IGNORED_PREFIXES:
        assert prefix in text
        assert "export-ignore" in text


def test_git_archive_excludes_ci_paths(tmp_path: Path) -> None:
    """Archive honors export-ignore in an isolated repo."""
    repo = tmp_path / "r"
    shutil.copytree(ROOT / "tests", repo / "tests")
    shutil.copytree(ROOT / ".github", repo / ".github")
    (repo / "Makefile").write_text("ci:\n\ttrue\n")
    (repo / "README.md").write_text("x\n")
    shutil.copy(ROOT / ".gitattributes", repo / ".gitattributes")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    blob = subprocess.check_output(["git", "archive", "HEAD"], cwd=repo)
    with tarfile.open(fileobj=BytesIO(blob), mode="r:*") as tar:
        names = tar.getnames()
    for prefix in IGNORED_PREFIXES:
        assert not any(n == prefix or n.startswith(prefix) for n in names), prefix
