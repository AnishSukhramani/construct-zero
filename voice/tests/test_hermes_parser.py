"""Hermes stdout parser fixtures."""

from __future__ import annotations

from construct_zero_voice.hermes_bridge import parse_hermes_reply


SAMPLE_BOX = """
╭─ Hermes Agent ───────────────────────────────────╮
│ PONG                                             │
╰──────────────────────────────────────────────────╯
"""


def test_parse_box():
    # Our regex captures body between Herms header and footer;
    # strip may leave pipe chars depending on format — assert content present
    out = parse_hermes_reply(SAMPLE_BOX)
    assert "PONG" in out


def test_parse_plain_after_init():
    raw = """
Initializing agent…
Hello from Hermes

Session: abc
"""
    out = parse_hermes_reply(raw)
    assert "Hello from Hermes" in out


def test_parse_strips_ansi():
    raw = "\x1b[32mInitializing agent\x1b[0m\n\x1b[1mReady\x1b[0m\n"
    out = parse_hermes_reply(raw)
    assert "Ready" in out
    assert "\x1b" not in out
