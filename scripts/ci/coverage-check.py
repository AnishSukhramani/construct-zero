#!/usr/bin/env python3
"""Run pytest-cov per package and enforce scripts/ci/coverage-floors.toml."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
FLOORS_FILE = ROOT / "scripts" / "ci" / "coverage-floors.toml"

PACKAGES: dict[str, dict[str, str]] = {
    "adapter": {
        "dir": "adapter",
        "cov": "construct_zero",
        "prefix": "adapter/src/construct_zero/",
    },
    "vpl": {
        "dir": "vpl",
        "cov": "construct_zero_vpl",
        "prefix": "vpl/src/construct_zero_vpl/",
    },
    "voice": {
        "dir": "voice",
        "cov": "construct_zero_voice",
        "prefix": "voice/src/construct_zero_voice/",
    },
}


def _load_floors() -> tuple[dict[str, int], dict[str, int]]:
    data = tomllib.loads(FLOORS_FILE.read_text())
    floors = {k: int(v) for k, v in data.get("floors", {}).items()}
    targets = {k: int(v) for k, v in data.get("targets", {}).items()}
    return floors, targets


def _run_pytest_cov(pkg: str, meta: dict[str, str]) -> dict:
    out_json = ROOT / meta["dir"] / ".coverage-report.json"
    test_targets = ["tests"]
    if pkg == "adapter":
        test_targets.append(str(ROOT / "tests" / "repo"))
    cmd = [
        "uv",
        "run",
        "pytest",
        "-q",
        *test_targets,
        f"--cov={meta['cov']}",
        f"--cov-report=json:{out_json}",
        "--cov-report=term-missing:skip-covered",
    ]
    subprocess.run(cmd, cwd=ROOT / meta["dir"], check=True)
    return json.loads(out_json.read_text())


def _report_suffix(rel_path: str, pkg_dir: str) -> str:
    prefix = f"{pkg_dir}/"
    if rel_path.startswith(prefix):
        return rel_path[len(prefix) :]
    return rel_path


def _file_percent(report: dict, rel_path: str, pkg_dir: str) -> float | None:
    files = report.get("files", {})
    suffix = _report_suffix(rel_path, pkg_dir)
    for k in (suffix, rel_path):
        if k in files:
            return float(files[k]["summary"]["percent_covered"])
    for k, entry in files.items():
        norm = k.replace("\\", "/")
        if norm.endswith(suffix) or norm.endswith(rel_path):
            return float(entry["summary"]["percent_covered"])
    return None


def _package_percent(report: dict) -> float:
    return float(report.get("totals", {}).get("percent_covered", 0.0))


def check_package(pkg: str) -> list[str]:
    meta = PACKAGES[pkg]
    floors, targets = _load_floors()
    report = _run_pytest_cov(pkg, meta)
    errors: list[str] = []
    floor = floors.get(pkg, 0)
    pct = _package_percent(report)
    if pct + 1e-6 < floor:
        errors.append(f"{pkg}: coverage {pct:.1f}% < floor {floor}%")
    for rel, target in targets.items():
        if not rel.startswith(meta["prefix"]):
            continue
        fpct = _file_percent(report, rel, meta["dir"])
        if fpct is None:
            errors.append(f"{pkg}: missing coverage entry for {rel}")
            continue
        if fpct + 1e-6 < target:
            errors.append(f"{pkg}: {rel} {fpct:.1f}% < target {target}%")
    print(f"{pkg}: total {pct:.1f}% (floor {floor}%)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package",
        choices=[*PACKAGES.keys(), "all"],
        default="all",
        help="Which package to check (default: all)",
    )
    args = parser.parse_args()
    pkgs = list(PACKAGES.keys()) if args.package == "all" else [args.package]
    errors: list[str] = []
    for pkg in pkgs:
        try:
            errors.extend(check_package(pkg))
        except subprocess.CalledProcessError as exc:
            errors.append(f"{pkg}: pytest failed ({exc.returncode})")
    if errors:
        for e in errors:
            print(f"coverage: {e}", file=sys.stderr)
        return 1
    print("coverage: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
