"""faster-whisper speech-to-text."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from construct_zero_voice.envcompat import env_cz

logger = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(self, model_size: str | None = None) -> None:
        self.model_size = (
            model_size
            or env_cz("VOICE_WHISPER_MODEL")
            or "base"
        ).strip()
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        device = env_cz("VOICE_WHISPER_DEVICE") or "auto"
        compute = env_cz("VOICE_WHISPER_COMPUTE") or "default"
        kwargs: dict = {"device": device}
        if compute != "default":
            kwargs["compute_type"] = compute
        # CPU-friendly default when device=auto fails in some envs
        try:
            self._model = WhisperModel(self.model_size, **kwargs)
        except Exception:
            logger.warning("Whisper device=%s failed; falling back to cpu int8", device)
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type="int8"
            )
        logger.info("faster-whisper loaded model=%s", self.model_size)

    def transcribe_bytes(self, data: bytes, suffix: str = ".webm") -> str:
        self.load()
        assert self._model is not None
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            return self.transcribe_path(path)
        finally:
            Path(path).unlink(missing_ok=True)

    def transcribe_path(self, path: str) -> str:
        self.load()
        assert self._model is not None
        segments, _info = self._model.transcribe(path, beam_size=1)
        parts = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
        return " ".join(parts).strip()
