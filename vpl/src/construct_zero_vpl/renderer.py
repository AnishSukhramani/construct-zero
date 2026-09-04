"""Prepare text excerpts for TTS (strip markdown noise)."""

from __future__ import annotations

import re

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_BOLD = re.compile(r"\*+([^*]+)\*+")
_MD_CODE = re.compile(r"`([^`]+)`")
_NUMBERED_PREFIX = re.compile(r"^\s*\d+\.\s*")


def render_for_speech(text: str) -> str:
    text = text or ""
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_CODE.sub(r"\1", text)
    lines = []
    for line in text.splitlines():
        line = _NUMBERED_PREFIX.sub("", line.strip())
        if line.startswith(("#", "-", "*", "|")):
            line = line.lstrip("#-*| ").strip()
        if line:
            lines.append(line)
    out = " ".join(lines) if lines else text.strip()
    out = re.sub(r"\s+", " ", out).strip()
    return out


def first_sentence(text: str, max_chars: int = 220) -> str:
    text = render_for_speech(text)
    if not text:
        return ""
    for sep in (". ", "? ", "! ", "\n"):
        idx = text.find(sep)
        if 0 < idx < max_chars:
            return text[: idx + 1].strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.strip() + "…"
