#!/usr/bin/env python3
"""Verify GitHub Action SHA pins match release tags (git ls-remote)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
ACTION_RE = re.compile(
    r"^\s*-\s*uses:\s+(?!\.)(?P<repo>[\w.-]+/[\w.-]+)@(?P<sha>[0-9a-f]{40})(?:\s+#\s+v(?P<tag>[\w.-]+))?\s*$"
)


def _collect_workflow_files() -> list[Path]:
    files = sorted(WORKFLOW_DIR.glob("*.yml"))
    files.extend(sorted(WORKFLOW_DIR.glob("*.yaml")))
    action_files = sorted((ROOT / ".github" / "actions").glob("**/action.yml"))
    action_files.extend(sorted((ROOT / ".github" / "actions").glob("**/action.yaml")))
    return files + action_files


def _parse_pins(paths: list[Path]) -> list[tuple[str, str, str, Path, int]]:
    """Return list of (repo, sha, tag, file, line)."""
    pins: list[tuple[str, str, str, Path, int]] = []
    for path in paths:
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            m = ACTION_RE.match(line)
            if not m:
                continue
            tag = m.group("tag") or ""
            pins.append((m.group("repo"), m.group("sha"), tag, path, lineno))
    return pins


def _tag_ref(tag: str) -> str:
    return tag if tag.startswith("v") else f"v{tag}"


def _ls_remote_tag_sha(repo: str, tag: str) -> str | None:
    url = f"https://github.com/{repo}"
    tref = _tag_ref(tag)
    for ref in (f"refs/tags/{tref}^{{}}", f"refs/tags/{tref}"):
        try:
            out = subprocess.check_output(
                ["git", "ls-remote", url, ref],
                text=True,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"git ls-remote failed for {repo} {ref}: {exc}") from exc
        line = out.strip().splitlines()
        if line:
            return line[0].split()[0]
    return None


def verify_pins(*, offline: bool = False) -> list[str]:
    paths = _collect_workflow_files()
    pins = _parse_pins(paths)
    if not pins:
        return ["no GitHub Action SHA pins found in workflows"]

    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for repo, sha, tag, path, lineno in pins:
        if not tag:
            errors.append(f"{path.relative_to(ROOT)}:{lineno}: missing # vX.Y.Z comment for {repo}@{sha[:7]}")
            continue
        key = (repo, sha, tag)
        if key in seen:
            continue
        seen.add(key)
        if offline:
            continue
        try:
            resolved = _ls_remote_tag_sha(repo, tag)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        if resolved is None:
            errors.append(f"{repo} tag v{tag} not found on GitHub")
            continue
        if resolved.lower() != sha.lower():
            errors.append(
                f"{repo}@{sha[:7]}… does not match v{tag} (resolved {resolved[:7]}…)"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Only check pin format/comments (no git ls-remote)",
    )
    args = parser.parse_args()
    errors = verify_pins(offline=args.offline)
    if errors:
        for err in errors:
            print(f"action-pins: {err}", file=sys.stderr)
        return 1
    mode = "offline format" if args.offline else "remote tags"
    print(f"action-pins: ok ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
