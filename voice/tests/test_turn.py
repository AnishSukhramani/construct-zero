"""/turn orchestration with mocked STT, Hermes, TTS."""

from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from hcx_voice.server import app, reset_backends, set_backends


class FakeSTT:
    model_size = "base"
    loaded = True
    calls: list[bytes]

    def __init__(self) -> None:
        self.calls = []

    def load(self) -> None:
        pass

    def transcribe_bytes(self, data: bytes, suffix: str = ".webm") -> str:
        self.calls.append(data)
        return "What time is it?"


class FakeTTS:
    voice = "af_heart"
    loaded = True
    last_error = None
    texts: list[str]

    def __init__(self) -> None:
        self.texts = []

    def load(self) -> None:
        pass

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, int]:
        self.texts.append(text)
        return b"fake-wav-bytes", 24000


def test_turn_order(monkeypatch):
    reset_backends()
    stt = FakeSTT()
    tts = FakeTTS()
    set_backends(stt=stt, tts=tts)

    order: list[str] = []

    def fake_ask(prompt: str, **kwargs):
        order.append("hermes")
        assert prompt == "What time is it?"
        return "It is noon."

    def fake_stt_wrap(data: bytes, suffix: str = ".webm") -> str:
        order.append("stt")
        return FakeSTT.transcribe_bytes(stt, data, suffix)

    def fake_tts_wrap(text: str, voice: str | None = None):
        order.append("tts")
        return FakeTTS.synthesize(tts, text, voice)

    stt.transcribe_bytes = fake_stt_wrap  # type: ignore[method-assign]
    tts.synthesize = fake_tts_wrap  # type: ignore[method-assign]

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
    assert data["content_type"] == "audio/wav"
    assert base64.b64decode(data["audio_base64"]) == b"fake-wav-bytes"
    assert order == ["stt", "hermes", "tts"]
    reset_backends()


def test_turn_empty_transcript(monkeypatch):
    reset_backends()

    class EmptySTT(FakeSTT):
        def transcribe_bytes(self, data: bytes, suffix: str = ".webm") -> str:
            return ""

    set_backends(stt=EmptySTT(), tts=FakeTTS())
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
