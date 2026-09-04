"""Structural parse of Markdown-ish assistant replies."""

from __future__ import annotations

import re
from math import ceil

from construct_zero_vpl.config import VplConfig
from construct_zero_vpl.models import Bucket, ListItem, SourceSpan, SpeechDocument
from construct_zero_vpl.renderer import render_for_speech

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_NUMBERED = re.compile(r"^\s*(\d+)\.\s+(.+)$")
_BULLET = re.compile(r"^\s*[-*•]\s+(.+)$")


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _label_from_item(text: str, max_words: int) -> str:
    clean = render_for_speech(text)
    words = clean.split()
    if len(words) <= max_words:
        return clean
    return " ".join(words[:max_words])


def _chunk_items(items: list[ListItem], max_buckets: int) -> list[list[ListItem]]:
    if not items:
        return []
    n = min(max_buckets, max(1, len(items)))
    size = ceil(len(items) / n)
    return [items[i : i + size] for i in range(0, len(items), size)]


def parse_document(full_text: str, config: VplConfig | None = None) -> SpeechDocument:
    config = config or VplConfig.from_env()
    text = full_text or ""
    lines = text.splitlines()

    intro_lines: list[str] = []
    items: list[ListItem] = []
    section_buckets: list[tuple[str, list[ListItem]]] = []
    current_section: str | None = None
    current_section_items: list[ListItem] = []
    char_pos = 0
    item_counter = 0

    def flush_section() -> None:
        nonlocal current_section, current_section_items
        if current_section and current_section_items:
            section_buckets.append((current_section, list(current_section_items)))
        current_section = None
        current_section_items = []

    for line in lines:
        line_start = char_pos
        line_end = char_pos + len(line)
        char_pos = line_end + 1  # newline

        hm = _HEADING.match(line)
        if hm:
            flush_section()
            current_section = hm.group(2).strip()
            continue

        nm = _NUMBERED.match(line)
        bm = _BULLET.match(line) if not nm else None
        body = None
        if nm:
            body = nm.group(2).strip()
        elif bm:
            body = bm.group(1).strip()

        if body:
            item_counter += 1
            item = ListItem(
                id=f"i{item_counter}",
                text=body,
                span=SourceSpan(start=line_start, end=line_end),
            )
            items.append(item)
            if current_section:
                current_section_items.append(item)
        elif line.strip() and not items and not section_buckets:
            intro_lines.append(line.strip())

    flush_section()

    buckets: list[Bucket] = []
    if section_buckets:
        for idx, (title, sec_items) in enumerate(section_buckets[: config.max_buckets]):
            buckets.append(
                Bucket(
                    id=f"b{idx}",
                    label=render_for_speech(title),
                    items=sec_items,
                )
            )
    elif items:
        for idx, chunk in enumerate(_chunk_items(items, config.max_buckets)):
            label = _label_from_item(chunk[0].text, config.label_max_words)
            buckets.append(Bucket(id=f"b{idx}", label=label, items=chunk))

    intro = "\n".join(intro_lines).strip()
    layered = False
    if config.enabled:
        if len(items) >= config.layer_threshold_items:
            layered = True
        elif _word_count(text) > config.passthrough_max_words and len(items) >= 3:
            layered = True

    return SpeechDocument(
        full_text=text,
        intro=intro,
        items=items,
        buckets=buckets,
        layered=layered,
    )
