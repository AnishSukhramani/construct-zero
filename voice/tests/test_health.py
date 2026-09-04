"""Health endpoint shape."""

from __future__ import annotations

from fastapi.testclient import TestClient

from construct_zero_voice.server import app, reset_backends, set_backends


class FakeSTT:
    model_size = "base"
    loaded = False

    def load(self) -> None:
        self.loaded = True

    def transcribe_bytes(self, data: bytes, suffix: str = ".webm") -> str:
        return "hello"


class FakeTTS:
    voice = "af_heart"
    loaded = False
    last_error = None

    def load(self) -> None:
        self.loaded = True

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, int]:
        return b"RIFF....WAV", 24000


def test_health_shape(monkeypatch):
    reset_backends()
    set_backends(stt=FakeSTT(), tts=FakeTTS())
    monkeypatch.setattr(
        "construct_zero_voice.server.check_adapter_up",
        lambda timeout=2.0: (True, "ok"),
    )
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
    assert data["stt"]["backend"] == "faster-whisper"
    assert data["tts"]["backend"] == "kokoro"
    assert "adapter" in data
    assert "hcx" in data  # deprecated alias
    assert "hermes" in data
    assert "cursor_key_present" in data
    reset_backends()
