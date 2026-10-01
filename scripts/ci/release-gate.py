#!/usr/bin/env python3
"""Release tag gate — validates versions/changelog/pin; never publishes."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    args = p.parse_args()
    tag = args.tag.lstrip("v")
    changelog = (ROOT / "CHANGELOG.md").read_text()
    if f"## [{tag}]" not in changelog and "## [Unreleased]" not in changelog:
        print("CHANGELOG missing section for tag", file=sys.stderr)
        return 1
    lock = (ROOT / "config/upstream.lock.yaml").read_text()
    m = re.search(r"ref:\s*([0-9a-f]{40})", lock)
    if not m:
        print("upstream.lock.yaml missing 40-char ref", file=sys.stderr)
        return 1
    for pkg in ("adapter", "vpl", "voice"):
        text = (ROOT / pkg / "pyproject.toml").read_text()
        if f'version = "{tag}"' not in text and tag not in text:
            print(f"version mismatch in {pkg} for tag {tag}", file=sys.stderr)
            return 1
    print("release-gate: ok (dry-run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
