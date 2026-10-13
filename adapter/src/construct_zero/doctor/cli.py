"""Entry point: python -m construct_zero.doctor.cli --certify [--json] [--offline]."""

from __future__ import annotations

import json
import os
import sys

from construct_zero.doctor.checks import build_context, run_check
from construct_zero.doctor.profiles import CZ_CERTIFIED_V1
from construct_zero.doctor.report import format_table, to_json


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] not in {"--certify"}:
        print(
            "Usage: python -m construct_zero.doctor.cli --certify [--json] [--offline]",
            file=sys.stderr,
        )
        return 2
    args = args[1:]
    as_json = False
    if "--json" in args:
        as_json = True
        args = [a for a in args if a != "--json"]
    if "--offline" in args:
        os.environ["CZ_DOCTOR_CERTIFY_OFFLINE"] = "1"
        args = [a for a in args if a != "--offline"]
    if args:
        print(f"Unknown arguments: {args}", file=sys.stderr)
        return 2

    profile = "cz-certified-v1"
    ctx = build_context()
    results = [run_check(spec, ctx) for spec in CZ_CERTIFIED_V1]

    backend_name = ctx["config"].inference.backend
    caps = None
    try:
        from construct_zero.core.registry import build, capabilities_for
        from construct_zero.core.sessions import SessionStore

        b = build(ctx["config"], SessionStore())
        backend_name = b.name
        c = capabilities_for(b)
        caps = {
            "tools": c.tools,
            "streaming": c.streaming,
            "vision": c.vision,
            "usage": c.usage,
            "max_context": c.max_context,
        }
    except Exception:
        pass

    if as_json:
        print(
            json.dumps(to_json(results, profile, backend=backend_name, capabilities=caps), indent=2)
        )
    else:
        print(format_table(results, profile), end="")

    required_fails = sum(1 for r in results if r.severity == "required" and r.status == "fail")
    return 0 if required_fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
