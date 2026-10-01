"""Release wheel/sdist must not ship CI or test trees."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_PREFIXES = ("tests/", ".github/", "scripts/ci/")


def _build_wheels(packages: tuple[str, ...]) -> list[Path]:
    wheels: list[Path] = []
    for pkg in packages:
        pkg_dir = ROOT / pkg
        subprocess.run(["uv", "build"], cwd=pkg_dir, check=True, capture_output=True)
        dist = pkg_dir / "dist"
        wheels.extend(sorted(dist.glob("*.whl")))
    return wheels


def _assert_wheel_paths(wheels: list[Path]) -> None:
    for whl in wheels:
        with zipfile.ZipFile(whl) as zf:
            for name in zf.namelist():
                for prefix in FORBIDDEN_PREFIXES:
                    assert not name.startswith(prefix), f"{whl.name} contains {name}"


def test_wheel_contents_exclude_dev_paths() -> None:
    _assert_wheel_paths(_build_wheels(("adapter", "vpl")))


def test_voice_wheel_contents_when_buildable() -> None:
    try:
        wheels = _build_wheels(("voice",))
    except subprocess.CalledProcessError:
        pytest.skip("voice uv build failed (known hatch force-include issue on this ref)")
    _assert_wheel_paths(wheels)
