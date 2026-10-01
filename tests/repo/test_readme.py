"""Repo-level checks for README launch plumbing (PR 10)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

CTA_MARKER = "**Using Construct Zero?**"
LANDING_HOST = "construct-zero.vercel.app"
UTM_PARAMS = ("utm_source=github", "utm_medium=readme", "utm_campaign=launch-oct26")
FORBIDDEN_PHRASE = "no paid features"

README_HEADINGS = [
    "## What it is",
    "## Requirements",
    "## Repo layout",
    "## Adapter API",
    "## Voice (hold-to-talk)",
    "## Updating",
    "## Tests",
    "## Success criteria (MVP)",
    "## Out of scope (for now)",
    "## Migration from HCX",
    "## For maintainers",
    "## License",
]

HELP_SETUP_REQUIRED_IDS = (
    "os",
    "install_method",
    "doctor_output",
    "hermes_version",
    "what_happened",
)

BADGE_PATTERNS = (
    re.compile(r"shields\.io", re.I),
    re.compile(r"!\[.*\]\(https://github\.com/.+/actions/", re.I),
    re.compile(r"!\[.*\]\(https://img\.shields\.io/", re.I),
)


def _readme_text(repo_root: Path) -> str:
    return (repo_root / "README.md").read_text(encoding="utf-8")


def test_cta_appears_exactly_twice(repo_root: Path) -> None:
    text = _readme_text(repo_root)
    assert text.count(CTA_MARKER) == 2


def test_readme_has_no_forbidden_phrase(repo_root: Path) -> None:
    text = _readme_text(repo_root).lower()
    assert FORBIDDEN_PHRASE not in text


def test_landing_links_include_utms(repo_root: Path) -> None:
    text = _readme_text(repo_root)
    landing_lines = [line for line in text.splitlines() if LANDING_HOST in line]
    assert landing_lines, "expected at least one landing-page link in README"
    for line in landing_lines:
        for param in UTM_PARAMS:
            assert param in line, f"missing {param} in landing link line: {line!r}"


def test_readme_headings_unchanged(repo_root: Path) -> None:
    text = _readme_text(repo_root)
    headings = [line.strip() for line in text.splitlines() if line.startswith("## ")]
    assert headings == README_HEADINGS


def test_readme_has_no_ci_badges(repo_root: Path) -> None:
    text = _readme_text(repo_root)
    for pattern in BADGE_PATTERNS:
        assert not pattern.search(text), f"unexpected badge pattern {pattern.pattern}"


def test_demo_video_link_present(repo_root: Path) -> None:
    text = _readme_text(repo_root)
    assert "https://youtu.be/wUiOjHTjId0" in text


def test_help_setup_discussion_template(repo_root: Path) -> None:
    path = repo_root / ".github" / "DISCUSSION_TEMPLATE" / "help-setup.yml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data.get("title")
    body = data.get("body")
    assert isinstance(body, list) and body

    field_ids = []
    doctor_labels = ""
    for block in body:
        if not isinstance(block, dict):
            continue
        fid = block.get("id")
        if fid:
            field_ids.append(fid)
        attrs = block.get("attributes") or {}
        if fid == "doctor_output":
            doctor_labels = f"{attrs.get('label', '')} {attrs.get('description', '')}"

    for required in HELP_SETUP_REQUIRED_IDS:
        assert required in field_ids, f"missing discussion field id {required!r}"

    assert "key" in doctor_labels.lower() or "secret" in doctor_labels.lower()


def test_issue_config_contact_link(repo_root: Path) -> None:
    path = repo_root / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    links = data.get("contact_links") or []
    help_links = [link for link in links if "help" in str(link.get("name", "")).lower()]
    assert help_links
    url = help_links[0].get("url", "")
    assert "discussions/categories/help-setup" in url
