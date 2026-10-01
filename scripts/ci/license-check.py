#!/usr/bin/env python3
"""Run pip-licenses against allowlist."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[2]
ALLOW = ROOT / "scripts" / "ci" / "license-allowlist.toml"

# pip-licenses strings → SPDX keys in license-allowlist.toml [allow]
LICENSE_ALIASES: dict[str, str] = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "Python Software Foundation License": "PSF-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}

LOCAL_PACKAGES = frozenset(
    {
        "construct-zero",
        "construct-zero-vpl",
        "construct-zero-voice",
    }
)


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


def _normalize_tokens(license_expr: str) -> list[str]:
    expr = (license_expr or "UNKNOWN").strip()
    if not expr or expr == "UNKNOWN":
        return ["UNKNOWN"]
    parts = re.split(r"\s*;\s*|\s+OR\s+", expr)
    out: list[str] = []
    for part in parts:
        token = part.strip()
        if not token:
            continue
        out.append(LICENSE_ALIASES.get(token, token))
    return out or ["UNKNOWN"]


def _license_allowed(
    license_expr: str,
    *,
    allowed: set[str],
    denied: set[str],
    allow_package: dict[str, str],
    pkg: str,
) -> tuple[bool, str | None]:
    raw = license_expr or "UNKNOWN"
    if pkg in allow_package and allow_package[pkg] == raw:
        return True, None
    for token in _normalize_tokens(raw):
        if token in allowed:
            continue
        if token in denied:
            return False, f"{pkg}: {raw} (denied: {token})"
        if pkg in allow_package:
            return False, f"{pkg}: {raw} (allow_package expects {allow_package[pkg]!r})"
        return False, f"{pkg}: {raw}"
    return True, None


def main() -> int:
    cfg = tomllib.loads(ALLOW.read_text())
    allowed = set(cfg.get("allow", {}).keys())
    denied = set(cfg.get("deny", {}).keys())
<<<<<<< HEAD
    review = set(cfg.get("review", {}).keys())
    allow_package: dict[str, str] = dict(cfg.get("allow_package", {}))
    unknown: list[str] = []
    denied_hits: list[str] = []
    flagged: list[str] = []
=======
    allow_package: dict[str, str] = dict(cfg.get("allow_package", {}))
    unknown: list[str] = []
    denied_hits: list[str] = []
>>>>>>> c1c99ec (test: complete API contract schemas, fixtures, wire uvicorn, conformance matrix)
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
            if pkg in LOCAL_PACKAGES:
                continue
<<<<<<< HEAD
            ok, err = _license_allowed(
                lic,
                allowed=allowed,
                denied=denied,
                allow_package=allow_package,
                pkg=pkg,
            )
            if ok:
                continue
            assert err is not None
            tokens = _normalize_tokens(lic)
            if any(t in review for t in tokens):
                flagged.append(f"{pkg} ({lic})")
=======
            if pkg in allow_package:
                if allow_package[pkg] == lic:
                    continue
                denied_hits.append(
                    f"{pkg}: {lic} (allow_package expects {allow_package[pkg]!r})"
                )
                continue
            if lic in denied:
                denied_hits.append(f"{pkg}: {lic}")
>>>>>>> c1c99ec (test: complete API contract schemas, fixtures, wire uvicorn, conformance matrix)
                continue
            if any(t in denied for t in tokens):
                denied_hits.append(err)
            else:
                unknown.append(err)
    if unknown:
        print("Unknown licenses (add to scripts/ci/license-allowlist.toml):", file=sys.stderr)
        for u in unknown:
            print(f"  {u}", file=sys.stderr)
        return 1
    if denied_hits:
        print("Denied licenses (allow via [allow_package] or remove dep):", file=sys.stderr)
        for d in denied_hits:
            print(f"  {d}", file=sys.stderr)
        return 1
<<<<<<< HEAD
    if flagged:
        print("Review flagged licenses:", *flagged, sep="\n  ")
=======
>>>>>>> c1c99ec (test: complete API contract schemas, fixtures, wire uvicorn, conformance matrix)
    print("license: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
