"""CLI for run, handoff (PR 19); extended in PR 20 for kill/usage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from construct_zero.home.runner import handoff_to, normalize_agent, run_agent


def _parse_run_args(rest: list[str]) -> tuple[list[str], list[str]]:
    if "--" in rest:
        idx = rest.index("--")
        return rest[:idx], rest[idx + 1 :]
    return rest, []


def cmd_run(args: argparse.Namespace) -> int:
    agent_args = args.agent_args or []
    try:
        result = run_agent(
            args.agent,
            agent_args,
            auto_handoff=args.auto_handoff,
            use_pty=not args.no_pty,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if result.quota_hit:
        print("Quota/limit detected; checkpoint written.", file=sys.stderr)
    if result.handoff_to:
        print(f"Auto-handoff launched: {result.handoff_to}", file=sys.stderr)
    return result.exit_code if result.exit_code is not None else 0


def cmd_handoff(args: argparse.Namespace) -> int:
    try:
        cmd = handoff_to(
            args.to,
            reason=args.reason,
            launch=not args.no_launch,
            from_agent=normalize_agent(args.from_agent or "manual"),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.no_launch:
        print(cmd)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv and argv[0] in ("run", "handoff", "kill", "unkill", "usage"):
        verb = argv[0]
        argv = argv[1:]
    else:
        verb = "run"
    if verb == "run":
        p = argparse.ArgumentParser(prog="construct-zero run")
        p.add_argument("agent", choices=["claude", "cursor", "hermes"])
        p.add_argument("--auto-handoff", action="store_true")
        p.add_argument("--no-pty", action="store_true")
        p.add_argument("agent_args", nargs=argparse.REMAINDER)
        args = p.parse_args(argv)
        if args.agent_args[:1] == ["--"]:
            args.agent_args = args.agent_args[1:]
        return cmd_run(args)
    if verb == "handoff":
        p = argparse.ArgumentParser(prog="construct-zero handoff")
        p.add_argument("--to", required=True, dest="to")
        p.add_argument("--reason", default="manual")
        p.add_argument("--no-launch", action="store_true")
        p.add_argument("--from-agent", default="manual")
        args = p.parse_args(argv)
        return cmd_handoff(args)
    print(f"command not implemented in this PR: {verb}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
