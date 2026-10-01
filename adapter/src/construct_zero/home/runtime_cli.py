"""CLI for run, handoff, kill, unkill, usage."""

from __future__ import annotations

import argparse
import json
import os
import sys
import httpx

from construct_zero.home import admin as cz_admin
from construct_zero.home import kill_registry as cz_kill_registry
from construct_zero.home import ledger as cz_ledger
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
    if verb == "kill":
        p = argparse.ArgumentParser(prog="construct-zero kill")
        p.add_argument("--reason", default="")
        args = p.parse_args(argv)
        return cmd_kill(args)
    if verb == "unkill":
        return cmd_unkill()
    if verb == "usage":
        p = argparse.ArgumentParser(prog="construct-zero usage")
        p.add_argument("--since", default=None)
        p.add_argument("--by", default="agent", choices=["agent", "day", "model"])
        p.add_argument("--json", action="store_true")
        args = p.parse_args(argv)
        return cmd_usage(args)
    print(f"unknown command: {verb}", file=sys.stderr)
    return 1


def _adapter_base() -> str:
    host = os.environ.get("CZ_HOST", "127.0.0.1")
    port = os.environ.get("CZ_PORT", "8765")
    return f"http://{host}:{port}"


def cmd_kill(args: argparse.Namespace) -> int:
    cz_admin.set_killed(args.reason)
    cz_kill_registry.terminate_all()
    key = cz_admin.ensure_admin_key()
    try:
        httpx.post(
            f"{_adapter_base()}/cz/v1/admin/kill",
            headers={"Authorization": f"Bearer {key}"},
            timeout=2.0,
        )
    except httpx.HTTPError:
        pass
    print("Kill switch engaged.")
    return 0


def cmd_unkill() -> int:
    cz_admin.clear_killed()
    key = cz_admin.ensure_admin_key()
    try:
        httpx.post(
            f"{_adapter_base()}/cz/v1/admin/unkill",
            headers={"Authorization": f"Bearer {key}"},
            timeout=2.0,
        )
    except httpx.HTTPError:
        pass
    print("Kill switch cleared.")
    return 0


def cmd_usage(args: argparse.Namespace) -> int:
    rows = cz_ledger.aggregate_usage(since=args.since, group_by=args.by)
    if args.json:
        print(json.dumps({"data": rows}, indent=2))
    else:
        for row in rows:
            print(f"{row['key']}\t{row['total_tokens']} tokens\t({row['requests']} reqs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
