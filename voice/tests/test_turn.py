"""/turn orchestration with mocked STT, Hermes, TTS, and VPL navigation."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient
from hcx_vpl.config import VplConfig
from hcx_vpl.engine import PresentationEngine

from hcx_voice.server import app, reset_backends, set_backends
from hcx_voice.session_store import SessionStore

FIXTURE = Path(__file__).resolve().parents[2] / "vpl" / "tests" / "fixtures" / "long_backlog.md"


class FakeSTT:
    model_size = "base"
    loaded = True

    def __init__(self, text: str = "What time is it?") -> None:
        self.text = text
        self.calls: list[bytes] = []

    def load(self) -> None:
        pass

    def transcribe_bytes(self, data: bytes, suffix: str = ".webm") -> str:
        self.calls.append(data)
        return self.text


class FakeTTS:
    voice = "af_heart"
    loaded = True
    last_error = None

    def __init__(self) -> None:
        self.texts: list[str] = []

    def load(self) -> None:
        pass

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, int]:
        self.texts.append(text)
        return b"fake-wav-bytes", 24000


def test_turn_order(monkeypatch):
    reset_backends()
    stt = FakeSTT()
    tts = FakeTTS()
    set_backends(
        stt=stt,
        tts=tts,
        vpl_engine=PresentationEngine(VplConfig(enabled=True)),
        session_store=SessionStore(),
    )

    order: list[str] = []

    def fake_ask(prompt: str, **kwargs):
        order.append("hermes")
        assert prompt == "What time is it?"
        return "It is noon."

    monkeypatch.setattr("hcx_voice.server.ask_hermes", fake_ask)

    client = TestClient(app)
    r = client.post(
        "/turn",
        files={"audio": ("u.webm", b"\x00\x01audio", "audio/webm")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["transcript"] == "What time is it?"
    assert data["reply"] == "It is noon."
    assert data["speak_text"] == "It is noon."
    assert data["mode"] == "passthrough"
    assert data["content_type"] == "audio/wav"
    assert base64.b64decode(data["audio_base64"]) == b"fake-wav-bytes"
    assert stt.calls
    assert tts.texts == ["It is noon."]
    assert order == ["hermes"]
    reset_backends()


def test_turn_layered_new_question(monkeypatch):
    reset_backends()
    backlog = FIXTURE.read_text(encoding="utf-8")
    tts = FakeTTS()
    set_backends(
        stt=FakeSTT("Give me the backlog"),
        tts=tts,
        vpl_engine=PresentationEngine(VplConfig(enabled=True, max_buckets=4)),
        session_store=SessionStore(),
    )

    hermes_calls = 0

    def fake_ask(prompt: str, **kwargs):
        nonlocal hermes_calls
        hermes_calls += 1
        return backlog

    monkeypatch.setattr("hcx_voice.server.ask_hermes", fake_ask)

    client = TestClient(app)
    r = client.post(
        "/turn",
        files={"audio": ("u.webm", b"audio", "audio/webm")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["reply"] == backlog
    assert data["session_id"]
    assert data["buckets"]
    assert len(data["speak_text"]) < len(backlog)
    assert hermes_calls == 1
    reset_backends()


def test_nav_turn_skips_hermes(monkeypatch):
    reset_backends()
    backlog = FIXTURE.read_text(encoding="utf-8")
    tts = FakeTTS()
    store = SessionStore()
    set_backends(
        stt=FakeSTT("second"),
        tts=tts,
        vpl_engine=PresentationEngine(VplConfig(enabled=True, max_buckets=4)),
        session_store=store,
    )

    hermes_calls = 0

    def fake_ask(prompt: str, **kwargs):
        nonlocal hermes_calls
        hermes_calls += 1
        return backlog

    monkeypatch.setattr("hcx_voice.server.ask_hermes", fake_ask)

    client = TestClient(app)

    # Seed session via first turn
    stt_first = FakeSTT("Give me the backlog")
    set_backends(stt=stt_first, tts=tts, vpl_engine=PresentationEngine(VplConfig(enabled=True)), session_store=store)
    r1 = client.post("/turn", files={"audio": ("u.webm", b"a", "audio/webm")})
    assert r1.status_code == 200
    session_id = r1.json()["session_id"]
    assert session_id
    assert hermes_calls == 1

    # Navigation turn — must not call Hermes again
    set_backends(stt=FakeSTT("second"), tts=tts, vpl_engine=PresentationEngine(VplConfig(enabled=True)), session_store=store)
    r2 = client.post(
        "/turn",
        files={"audio": ("u.webm", b"b", "audio/webm")},
        headers={"X-Session-Id": session_id},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["reply"] == backlog
    assert data["mode"] == "deepen"
    assert hermes_calls == 1
    reset_backends()


def test_turn_empty_transcript(monkeypatch):
    reset_backends()
    set_backends(
        stt=FakeSTT(""),
        tts=FakeTTS(),
        vpl_engine=PresentationEngine(VplConfig(enabled=True)),
        session_store=SessionStore(),
    )
    monkeypatch.setattr(
        "hcx_voice.server.ask_hermes",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call hermes")),
    )
    client = TestClient(app)
    r = client.post(
        "/turn",
        files={"audio": ("u.webm", b"x", "audio/webm")},
    )
    assert r.status_code == 400
    reset_backends()
