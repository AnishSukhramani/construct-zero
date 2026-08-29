"""Kokoro-82M text-to-speech (official kokoro package)."""

from __future__ import annotations

import io
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class KokoroTTS:
    def __init__(self, voice: str | None = None, lang_code: str = "a") -> None:
        self.voice = (voice or os.environ.get("HCX_VOICE_KOKORO_VOICE") or "af_heart").strip()
        self.lang_code = lang_code
        self._pipeline: Any = None
        self._error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def last_error(self) -> str | None:
        return self._error

    def load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code=self.lang_code)
            self._error = None
            logger.info("Kokoro TTS loaded voice=%s lang=%s", self.voice, self.lang_code)
        except Exception as exc:
            self._error = str(exc)
            logger.exception("Kokoro load failed")
            raise

    def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, int]:
        """Return (wav_bytes, sample_rate)."""
        text = (text or "").strip()
        if not text:
            raise ValueError("empty text")
        self.load()
        assert self._pipeline is not None
        import numpy as np
        import soundfile as sf

        use_voice = (voice or self.voice).strip()
        chunks: list = []
        sample_rate = 24000
        for _gs, _ps, audio in self._pipeline(text, voice=use_voice, speed=1.0):
            arr = np.asarray(audio, dtype=np.float32)
            if arr.size:
                chunks.append(arr)
        if not chunks:
            raise RuntimeError("Kokoro produced no audio")
        audio_out = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, audio_out, sample_rate, format="WAV")
        return buf.getvalue(), sample_rate
