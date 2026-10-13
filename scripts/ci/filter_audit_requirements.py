#!/usr/bin/env python3
"""Drop editable/path requirements from a uv export before pip-audit (hashed third-party only)."""

from __future__ import annotations

import sys
from pathlib import Path


def filter_requirements(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("-e ") or "file://" in stripped:
            i += 1
            while i < len(lines) and (
                lines[i].startswith((" ", "\t"))
                or lines[i].strip().startswith("#")
                or lines[i].strip() == ""
            ):
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.write_text(filter_requirements(src.read_text()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
