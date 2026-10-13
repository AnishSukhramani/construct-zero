#!/usr/bin/env python3
"""No-op unless config/upstream.lock.yaml changed on a PR (then require label + body section)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        print("pin-bump: no-op (not a PR)")
        return 0
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        cwd=ROOT,
        text=True,
    )
    if "config/upstream.lock.yaml" not in diff:
        print("pin-bump: no-op (lock unchanged)")
        return 0
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    body = (event.get("pull_request") or {}).get("body") or ""
    labels = {lb["name"] for lb in (event.get("pull_request") or {}).get("labels", [])}
    if "pin-bump-approved" not in labels:
        print("pin-bump: lock changed but label pin-bump-approved missing", file=sys.stderr)
        return 1
    if "## Pin bump" not in body:
        print("pin-bump: missing ## Pin bump section", file=sys.stderr)
        return 1
    print("pin-bump: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
