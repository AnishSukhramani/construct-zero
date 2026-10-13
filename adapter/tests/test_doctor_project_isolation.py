"""Doctor certify: project isolation check."""

from __future__ import annotations

from pathlib import Path

import pytest
from construct_zero.doctor.checks import _check_project_isolation


def test_project_isolation_passes_for_nested_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "app"
    install = project / "construct-zero"
    install.mkdir(parents=True)
    (project / ".git").mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    monkeypatch.chdir(install)
    status, detail = _check_project_isolation({})
    assert status == "pass"
    assert "app" in detail.replace("\\", "/")


def test_project_isolation_fails_when_root_is_cz_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "app"
    install = project / "construct-zero"
    install.mkdir(parents=True)
    (project / ".git").mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    monkeypatch.setenv("CZ_PROJECT_ROOT", str(install))
    status, _detail = _check_project_isolation({})
    assert status == "fail"
