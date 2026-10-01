"""Quota / limit detection from agent output."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


@lru_cache
def _load_patterns() -> dict[str, list[str]]:
    path = Path(__file__).with_name("quota_patterns.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agents = data.get("agents") or {}
    out: dict[str, list[str]] = {}
    for aid, spec in agents.items():
        out[str(aid)] = [str(p).lower() for p in (spec.get("patterns") or [])]
    return out


def match_quota(agent_id: str, stream_text: str) -> bool:
    patterns = _load_patterns().get(agent_id, [])
    clean = strip_ansi(stream_text).lower()
    if "cz_budget_exceeded" in clean:
        return True
    return any(p in clean for p in patterns)
