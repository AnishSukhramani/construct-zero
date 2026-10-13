#!/usr/bin/env python3
"""Ensure runtime packages do not embed third-party telemetry."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = (
    ROOT / "adapter" / "src" / "construct_zero",
    ROOT / "voice" / "src" / "construct_zero_voice",
    ROOT / "vpl" / "src" / "construct_zero_vpl",
)

FORBIDDEN = re.compile(
    r"(sentry_sdk|segment\.|amplitude|mixpanel|posthog|datadog|newrelic|google-analytics|gtag\()",
    re.I,
)


def main() -> int:
    errors: list[str] = []
    for base in SCAN_ROOTS:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if FORBIDDEN.search(text):
                errors.append(f"forbidden telemetry marker in {path.relative_to(ROOT)}")
            if "import requests" in text or "from requests" in text:
                errors.append(f"requests library in {path.relative_to(ROOT)}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("telemetry_check: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
