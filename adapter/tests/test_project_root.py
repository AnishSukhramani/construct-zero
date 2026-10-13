"""Project root vs CZ install detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from construct_zero.security.project_root import (
    agent_context_is_cz_source,
    is_nested_cz_install,
    relative_cz_install_path,
    resolve_user_project_root,
)


def test_nested_construct_zero_uses_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "myapp"
    install = project / "construct-zero"
    install.mkdir(parents=True)
    (project / ".git").mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    monkeypatch.chdir(install)
    assert is_nested_cz_install(install)
    assert resolve_user_project_root() == project.resolve()
    assert not agent_context_is_cz_source()


def test_standalone_install_uses_self(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install = tmp_path / "my-agent"
    install.mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    monkeypatch.chdir(install)
    assert not is_nested_cz_install(install)
    assert resolve_user_project_root() == install.resolve()


def test_relative_install_path_and_misconfigured_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "app"
    install = project / "construct-zero"
    install.mkdir(parents=True)
    monkeypatch.setenv("CZ_ROOT", str(install))
    assert relative_cz_install_path(project) == "construct-zero"
    monkeypatch.setenv("CZ_PROJECT_ROOT", str(install))
    assert agent_context_is_cz_source()


def test_explicit_project_root_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install = tmp_path / "construct-zero"
    project = tmp_path / "app"
    install.mkdir()
    project.mkdir()
    monkeypatch.setenv("CZ_ROOT", str(install))
    monkeypatch.setenv("CZ_PROJECT_ROOT", str(project))
    assert resolve_user_project_root() == project.resolve()
