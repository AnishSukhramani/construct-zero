"""Release wheel/sdist must not ship CI or test trees."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

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


def test_wheel_contents_exclude_dev_paths() -> None:
    wheels = _build_wheels(("adapter", "vpl", "voice"))
    assert len(wheels) >= 3
    for whl in wheels:
        with zipfile.ZipFile(whl) as zf:
            for name in zf.namelist():
                for prefix in FORBIDDEN_PREFIXES:
                    assert not name.startswith(prefix), f"{whl.name} contains {name}"
