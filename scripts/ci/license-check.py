#!/usr/bin/env python3
"""Run pip-licenses against allowlist."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[2]
ALLOW = ROOT / "scripts" / "ci" / "license-allowlist.toml"


def _pip_licenses_bin() -> Path:
    return ROOT / "adapter" / ".venv" / "bin" / "pip-licenses"


def _licenses_for(pkg_dir: Path) -> list[dict]:
    bin_path = _pip_licenses_bin()
    if not bin_path.is_file():
        raise FileNotFoundError("pip-licenses not installed in adapter venv")
    out = subprocess.check_output(
        [str(bin_path), "--format=json"],
        cwd=pkg_dir,
        text=True,
    )
    return json.loads(out)


def main() -> int:
    cfg = tomllib.loads(ALLOW.read_text())
    allowed = set(cfg.get("allow", {}).keys())
    review = set(cfg.get("review", {}).keys())
    unknown: list[str] = []
    flagged: list[str] = []
    for name in ("adapter", "vpl", "voice"):
        pkg_dir = ROOT / name
        subprocess.run(
            ["uv", "sync", "--locked", "--extra", "dev"],
            cwd=pkg_dir,
            check=True,
            capture_output=True,
        )
        for row in _licenses_for(pkg_dir):
            lic = row.get("License") or "UNKNOWN"
            pkg = row.get("Name", "?")
            if lic in allowed:
                continue
            if lic in review:
                flagged.append(f"{pkg} ({lic})")
                continue
            unknown.append(f"{pkg}: {lic}")
    if unknown:
        print("Unknown licenses (add to scripts/ci/license-allowlist.toml):", file=sys.stderr)
        for u in unknown:
            print(f"  {u}", file=sys.stderr)
        return 1
    if flagged:
        print("Review flagged licenses:", *flagged, sep="\n  ")
    print("license: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
