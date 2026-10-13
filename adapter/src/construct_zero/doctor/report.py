"""Human-readable and JSON reports for --certify."""

from __future__ import annotations

import platform
import re
from datetime import datetime, timezone
from typing import Any

from construct_zero import __version__
from construct_zero.doctor.checks import CheckResult


def _redact_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _redact_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_json(v) for v in obj]
    if isinstance(obj, str):
        s = obj.replace(str(__import__("pathlib").Path.home()), "~")
        s = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-REDACTED", s)
        s = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "127.0.0.1", s)
        return s
    return obj


def format_table(results: list[CheckResult], profile: str) -> str:
    lines = [f"==> CZ Certified profile: {profile}", ""]
    for r in results:
        mark = {"pass": "OK", "fail": "FAIL", "skip": "SKIP", "warn": "WARN"}.get(
            r.status, r.status
        )
        lines.append(f"  [{mark}] {r.id}: {r.detail}")
        if r.status == "fail":
            lines.append(f"         Fix: {r.fix}")
    required_fails = sum(1 for r in results if r.severity == "required" and r.status == "fail")
    lines.append("")
    if required_fails:
        lines.append(f"NOT CERTIFIED: {required_fails} required check(s) failed")
    else:
        lines.append(f"CERTIFIED ({profile})")
    return "\n".join(lines) + "\n"


def to_json(
    results: list[CheckResult],
    profile: str,
    *,
    backend: str,
    capabilities: dict[str, Any] | None,
) -> dict[str, Any]:
    certified = not any(r.severity == "required" and r.status == "fail" for r in results)
    payload = {
        "schema": "cz-doctor/1",
        "profile": profile,
        "certified": certified,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cz": {"version": __version__, "commit": None},
        "env": {
            "os": f"{platform.system()} {platform.release()} {platform.machine()}",
            "python": platform.python_version(),
        },
        "hermes": {"pin": None, "head": None},
        "backend": {"name": backend, "capabilities": capabilities or {}},
        "checks": [
            {
                "id": r.id,
                "severity": r.severity,
                "status": r.status,
                "detail": r.detail,
                "fix": r.fix,
            }
            for r in results
        ],
    }
    return _redact_json(payload)
