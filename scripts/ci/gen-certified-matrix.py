#!/usr/bin/env python3
"""Generate docs/certified.md from scripts/ci/certified-matrix.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "scripts" / "ci" / "certified-matrix.yaml"
OUT = ROOT / "docs" / "certified.md"


def render(data: dict) -> str:
    profile = data.get("profile", "cz-certified-v1")
    lines = [
        "# CZ Certified matrix",
        "",
        f"Profile: **{profile}**. Generated from `scripts/ci/certified-matrix.yaml`.",
        "",
        "| OS | Python | Hermes pin | Backend | Client | Status |",
        "|----|--------|------------|---------|--------|--------|",
    ]
    for cell in data.get("cells") or []:
        lines.append(
            "| {os} | {python} | {hermes_pin} | {backend} | {client} | {status} |".format(
                **cell
            )
        )
    lines.extend(
        [
            "",
            "Run locally: `./construct-zero doctor --certify [--json] [--offline]`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Exit 1 if docs/certified.md is stale")
    args = parser.parse_args()
    data = yaml.safe_load(MATRIX.read_text()) or {}
    content = render(data)
    if args.check:
        if not OUT.is_file():
            print(f"missing {OUT}", file=sys.stderr)
            return 1
        if OUT.read_text() != content:
            print(
                "docs/certified.md is out of date; run scripts/ci/gen-certified-matrix.py",
                file=sys.stderr,
            )
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
