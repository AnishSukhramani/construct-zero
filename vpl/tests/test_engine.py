"""Presentation engine FSM and extractive speak text."""

from __future__ import annotations

from pathlib import Path

from hcx_vpl.config import VplConfig
from hcx_vpl.engine import PresentationEngine
from hcx_vpl.intents import is_navigation_intent

FIXTURES = Path(__file__).parent / "fixtures"


def test_sixteen_item_orient_shorter_than_full():
    text = (FIXTURES / "long_backlog.md").read_text(encoding="utf-8")
    engine = PresentationEngine(VplConfig(enabled=True, max_buckets=4))
    session, turn = engine.begin(text)
    assert turn.layered
    assert turn.reply_full == text
    assert len(turn.speak_text) < len(text)
    assert turn.session_id
    assert turn.buckets
    assert session is not None


def test_nav_turn_uses_step_not_prepare():
    text = (FIXTURES / "long_backlog.md").read_text(encoding="utf-8")
    engine = PresentationEngine(VplConfig(enabled=True))
    session, _ = engine.begin(text)
    assert session is not None
    assert is_navigation_intent("second", session.document.buckets)
    updated, nav = engine.step(session, "second")
    assert nav.mode == "deepen"
    assert nav.reply_full == text
    assert updated is not None


def test_passthrough_short():
    engine = PresentationEngine(VplConfig(enabled=True))
    session, turn = engine.begin("PONG")
    assert session is None
    assert turn.mode == "passthrough"
    assert turn.speak_text == "PONG"
