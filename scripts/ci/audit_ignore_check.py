#!/usr/bin/env python3
"""Validate audit-ignore.toml expiry dates."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts" / "ci" / "audit-ignore.toml"


def main() -> int:
    data = tomllib.loads(PATH.read_text())
    today = date.today()
    expired = []
    for row in data.get("ignore", []):
        exp = row.get("expires", "")
        if not exp:
            continue
        if date.fromisoformat(exp) < today and row.get("id") != "PLACEHOLDER-0000":
            expired.append(row["id"])
    if expired:
        print(f"audit-ignore: expired entries: {expired}", file=sys.stderr)
        return 1
    print("audit-ignore: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
