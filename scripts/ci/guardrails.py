#!/usr/bin/env python3
"""PR diff policy checks (tests, deletions, protected paths, coverage floors)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FLOORS_FILE = ROOT / "scripts" / "ci" / "coverage-floors.toml"

PROTECTED_PREFIXES = (
    "install.sh",
    "config/upstream.lock.yaml",
    ".github/",
    "scripts/doctor.sh",
    "scripts/ci/",
    "Makefile",
    ".gitattributes",
)
PROTECTED_SUFFIXES = ("uv.lock",)

SRC_PREFIXES = ("adapter/src/", "vpl/src/", "voice/src/", "hermes-plugin/")
SCRIPTS_PREFIX = "scripts/"
TEST_MARKERS = (
    "pytest.mark.skip",
    "pytest.mark.skipif",
    "pytest.mark.xfail",
    "@pytest.mark.skip",
    "@pytest.mark.skipif",
    "@pytest.mark.xfail",
    "pytest.skip(",
    "pytest.xfail(",
)


def _run(cmd: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.STDOUT)


def _changed_files(base: str, *, repo_root: Path) -> list[str]:
    out = _run(["git", "diff", "--name-only", f"{base}...HEAD"], cwd=repo_root)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _deleted_files(base: str, *, repo_root: Path) -> list[str]:
    out = _run(
        ["git", "diff", "--name-only", "--diff-filter=D", f"{base}...HEAD"],
        cwd=repo_root,
    )
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _diff_text(base: str, *, repo_root: Path) -> str:
    return _run(["git", "diff", f"{base}...HEAD"], cwd=repo_root)


def _is_test_path(path: str) -> bool:
    if "/tests/" in path or path.startswith("tests/"):
        return True
    if path.endswith("_test.py") or path.startswith("test_"):
        return True
    return False


def _is_protected(path: str) -> bool:
    for p in PROTECTED_PREFIXES:
        if path == p or path.startswith(p):
            return True
    if path.endswith("uv.lock") or path.split("/")[-1] == "uv.lock":
        return True
    return False


def _parse_floor_values(text: str) -> dict[str, int]:
    floors: dict[str, int] = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().strip('"')
        val = val.strip().split()[0]
        try:
            num = int(val)
        except ValueError:
            continue
        if section == "floors":
            floors[key] = num
    return floors


def _github_api(path: str, token: str) -> dict | list | None:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def _pr_labels_and_body(event_path: Path) -> tuple[set[str], str, str | None, str | None]:
    data = json.loads(event_path.read_text())
    pr = data.get("pull_request") or {}
    body = pr.get("body") or ""
    labels = {lb["name"] for lb in pr.get("labels", [])}
    base_sha = (pr.get("base") or {}).get("sha")
    repo = data.get("repository", {})
    full = repo.get("full_name", "")
    number = pr.get("number")
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and full and number:
        issue = _github_api(f"/repos/{full}/issues/{number}", token)
        if isinstance(issue, dict):
            labels = {lb["name"] for lb in issue.get("labels", [])}
            body = issue.get("body") or body
        events = _github_api(f"/repos/{full}/issues/{number}/events", token)
        if isinstance(events, list):
            for ev in reversed(events):
                if ev.get("event") == "labeled":
                    actor = (ev.get("actor") or {}).get("login")
                    if actor and actor != "AnishSukhramani":
                        pass  # best-effort only; documented limitation
                    break
    return labels, body, full, base_sha


def check(
    *,
    base: str,
    labels: set[str],
    pr_body: str,
    local: bool,
    repo_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    files = _changed_files(base, repo_root=repo_root)
    diff = _diff_text(base, repo_root=repo_root)

    src_or_scripts = [
        f
        for f in files
        if any(f.startswith(p) for p in SRC_PREFIXES)
        or (f.startswith(SCRIPTS_PREFIX) and not f.startswith("scripts/ci/guardrails"))
    ]
    tests = [f for f in files if _is_test_path(f)]
    if src_or_scripts and not tests and "no-test-needed" not in labels:
        errors.append(
            "Source/scripts changed without test updates. Add tests or obtain the "
            "`no-test-needed` label (Anish only)."
        )

    deleted_tests = [f for f in _deleted_files(base, repo_root=repo_root) if _is_test_path(f)]
    skip_added = False
    for path in files:
        if not _is_test_path(path):
            continue
        try:
            chunk = _run(["git", "diff", f"{base}...HEAD", "--", path], cwd=repo_root)
        except subprocess.CalledProcessError:
            continue
        if any(m in chunk for m in TEST_MARKERS):
            skip_added = True
            break
    if (deleted_tests or skip_added) and "test-change-approved" not in labels:
        errors.append(
            "Test deletion or skip/xfail requires the `test-change-approved` label."
        )

    floors_path = repo_root / FLOORS_FILE.relative_to(ROOT)
    if floors_path.exists() and "coverage-floors.toml" in diff:
        try:
            old_text = _run(
                ["git", "show", f"{base}:{FLOORS_FILE.relative_to(ROOT)}"],
                cwd=repo_root,
            )
        except subprocess.CalledProcessError:
            old_text = ""
        new_text = floors_path.read_text()
        old_f = _parse_floor_values(old_text)
        new_f = _parse_floor_values(new_text)
        lowered = [k for k, v in old_f.items() if k in new_f and new_f[k] < v]
        if lowered and "test-change-approved" not in labels:
            errors.append(
                f"Coverage floor lowered for {lowered} — needs `test-change-approved`."
            )

    protected = [f for f in files if _is_protected(f)]
    if protected and not local:
        if "## Protected paths" not in pr_body:
            errors.append(
                "Protected paths touched but PR body lacks a `## Protected paths` section."
            )
        else:
            for p in protected:
                if p not in pr_body and Path(p).name not in pr_body:
                    errors.append(f"Protected path `{p}` not mentioned in `## Protected paths`.")

    if local and errors:
        errors.insert(0, "(local guardrails — labels not applied; CI re-checks on PR)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Diff against merge-base locally")
    parser.add_argument("--base", default="", help="Override diff base ref")
    args = parser.parse_args()

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name == "push":
        print("guardrails: push event — success (no-op)")
        return 0

    labels: set[str] = set()
    pr_body = os.environ.get("GUARDRAILS_PR_BODY", "")
    base = args.base

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).is_file():
        labels, pr_body, _repo, pr_base = _pr_labels_and_body(Path(event_path))
        if pr_base:
            base = pr_base
        if not base:
            try:
                base = _run(["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT).strip()
            except subprocess.CalledProcessError:
                pass
    elif args.local:
        base = base or "origin/main"
        try:
            _run(["git", "merge-base", "HEAD", base], cwd=ROOT)
        except subprocess.CalledProcessError:
            base = "HEAD~1"
        merge = _run(["git", "merge-base", "HEAD", base], cwd=ROOT).strip()
        base = merge
    else:
        print("guardrails: no PR context — success (no-op)")
        return 0

    if not base:
        print("guardrails: no base ref")
        return 1

    errors = check(base=base, labels=labels, pr_body=pr_body, local=args.local)
    if errors:
        for e in errors:
            print(f"guardrails: {e}", file=sys.stderr)
        return 1
    print("guardrails: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
