"""CLI for `construct-zero home …` (invoked from repo dispatcher)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from construct_zero.home import registry as reg_mod
from construct_zero.home.pointers import apply_pointers, git_exclude_cz, remove_pointers
from construct_zero.home.store import CzStore


def _cmd_init(args: argparse.Namespace) -> int:
    project = Path.cwd()
    store = CzStore(project)
    created = store.init_scaffold()
    git_exclude_cz(project, commit_mode=args.commit)
    touched: list[str] = []
    try:
        touched = apply_pointers(
            project,
            skip_pointers=args.no_pointers,
            hermes_memory=args.hermes_memory,
            assume_yes=args.yes,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    reg_mod.sync_registry()
    reg_mod.register_project(project, touched)
    if created:
        print("Created:", ", ".join(created))
    else:
        print("`.cz/` already initialized (no scaffold changes).")
    if touched:
        print("Pointers updated:", ", ".join(touched))
    return 0


def _cmd_status(_args: argparse.Namespace) -> int:
    store = CzStore()
    summary = store.status_summary()
    reg = reg_mod.load_registry()
    print(json.dumps({"store": summary, "registry_agents": [a.id for a in reg.agents]}, indent=2))
    return 0


def _cmd_agents(args: argparse.Namespace) -> int:
    if args.key_action == "key":
        if not args.agent_id:
            print("usage: home agents key <id>", file=sys.stderr)
            return 2
        from construct_zero.home.identity import issue_agent_key

        token = issue_agent_key(args.agent_id)
        print(token)
        return 0
    reg = reg_mod.sync_registry()
    print(json.dumps(reg.to_dict()["agents"], indent=2))
    return 0


def _cmd_sync(_args: argparse.Namespace) -> int:
    reg_mod.sync_registry()
    print("Registry synced.")
    return 0


def _cmd_uninstall(_args: argparse.Namespace) -> int:
    removed = remove_pointers(Path.cwd())
    if removed:
        print("Removed pointer blocks from:", ", ".join(removed))
    else:
        print("No CZ pointer blocks found.")
    return 0


def _cmd_memory(args: argparse.Namespace) -> int:
    store = CzStore()
    if not store.exists():
        store.init_scaffold()
    action = args.memory_action
    if action == "add":
        eid = store.memory_add(args.title, args.body or "", by=args.by)
        print(eid)
        return 0
    if action == "list":
        entries = store.memory_list(include_all=args.all)
        for e in entries:
            print(e.entry_id, "·", e.title)
        return 0
    if action == "supersede":
        store.memory_supersede(args.entry_id, args.title, args.body or "")
        print("superseded", args.entry_id)
        return 0
    if action == "expire":
        store.memory_expire(args.entry_id)
        print("expired", args.entry_id)
        return 0
    print("unknown memory action", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="construct-zero home")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create .cz/ and pointer files")
    init.add_argument("--commit", action="store_true", help="Do not add .cz/ to git exclude")
    init.add_argument("--no-pointers", action="store_true")
    init.add_argument("--hermes-memory", action="store_true")
    init.add_argument("--yes", action="store_true", help="Skip tracked-file confirmation")
    init.set_defaults(func=_cmd_init)

    sub.add_parser("status").set_defaults(func=_cmd_status)
    agents = sub.add_parser("agents", help="List detected agents")
    agents_sub = agents.add_subparsers(dest="key_action")
    key_p = agents_sub.add_parser("key")
    key_p.add_argument("agent_id")
    key_p.set_defaults(key_action="key")
    agents.set_defaults(key_action=None)
    agents.set_defaults(func=_cmd_agents)

    sub.add_parser("sync").set_defaults(func=_cmd_sync)
    sub.add_parser("uninstall", help="Remove managed pointer blocks only").set_defaults(
        func=_cmd_uninstall
    )

    mem = sub.add_parser("memory", help="Memory entry commands")
    mem_sub = mem.add_subparsers(dest="memory_action", required=True)
    add = mem_sub.add_parser("add")
    add.add_argument("title")
    add.add_argument("body", nargs="?", default="")
    add.add_argument("--by", default="user")
    add.set_defaults(func=_cmd_memory)

    lst = mem_sub.add_parser("list")
    lst.add_argument("--all", action="store_true")
    lst.set_defaults(func=_cmd_memory)

    sup = mem_sub.add_parser("supersede")
    sup.add_argument("entry_id")
    sup.add_argument("title")
    sup.add_argument("body", nargs="?", default="")
    sup.set_defaults(func=_cmd_memory)

    exp = mem_sub.add_parser("expire")
    exp.add_argument("entry_id")
    exp.set_defaults(func=_cmd_memory)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
