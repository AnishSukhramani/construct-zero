"""Parser and layered-mode heuristics."""

from __future__ import annotations

from pathlib import Path

from construct_zero_vpl.config import VplConfig
from construct_zero_vpl.parser import parse_document

FIXTURES = Path(__file__).parent / "fixtures"


def test_short_reply_passthrough():
    doc = parse_document("PONG", VplConfig(enabled=True))
    assert not doc.layered
    assert doc.full_text == "PONG"


def test_long_backlog_layered_and_bucketed():
    text = (FIXTURES / "long_backlog.md").read_text(encoding="utf-8")
    doc = parse_document(text, VplConfig(enabled=True, max_buckets=4))
    assert doc.layered
    assert len(doc.items) == 16
    assert 1 <= len(doc.buckets) <= 4
    assert doc.full_text == text


def test_speak_spans_subset_of_source():
    text = (FIXTURES / "long_backlog.md").read_text(encoding="utf-8")
    doc = parse_document(text, VplConfig(enabled=True))
    for item in doc.items:
        excerpt = doc.full_text[item.span.start : item.span.end]
        assert item.text in excerpt or excerpt.strip() in item.text
