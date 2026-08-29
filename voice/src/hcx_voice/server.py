"""FastAPI voice sidecar: /health /stt /tts /turn + hold-to-talk UI."""

from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hcx_voice import __version__
from hcx_voice.hermes_bridge import ask_hermes, check_hcx_up
from hcx_voice.stt_whisper import WhisperSTT
from hcx_voice.tts_kokoro import KokoroTTS

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

_stt: WhisperSTT | None = None
_tts: KokoroTTS | None = None


def get_stt() -> WhisperSTT:
    global _stt
    if _stt is None:
        _stt = WhisperSTT()
    return _stt


def get_tts() -> KokoroTTS:
    global _tts
    if _tts is None:
        _tts = KokoroTTS()
    return _tts


def set_backends(stt: WhisperSTT | None = None, tts: KokoroTTS | None = None) -> None:
    """Test hook to inject mock backends."""
    global _stt, _tts
    if stt is not None:
        _stt = stt
    if tts is not None:
        _tts = tts


def reset_backends() -> None:
    global _stt, _tts
    _stt = None
    _tts = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    preload = os.environ.get("HCX_VOICE_PRELOAD", "").strip() in ("1", "true", "yes")
    if preload:
        try:
            get_stt().load()
        except Exception:
            logger.exception("STT preload failed")
        try:
            get_tts().load()
        except Exception:
            logger.exception("TTS preload failed")
    yield


app = FastAPI(title="HCX Voice", version=__version__, lifespan=lifespan)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str | None = None


class TurnResponse(BaseModel):
    transcript: str
    reply: str
    audio_base64: str
    content_type: str = "audio/wav"


@app.get("/health")
def health() -> dict[str, Any]:
    stt = get_stt()
    tts = get_tts()
    hcx_ok, hcx_detail = check_hcx_up()
    hermes_ok = False
    hermes_detail = "not checked"
    try:
        from hcx_voice.hermes_bridge import default_hermes_bin

        hb = default_hermes_bin()
        hermes_ok = hb.exists() if isinstance(hb, Path) else True
        hermes_detail = str(hb)
        if not Path(str(hb)).exists() and str(hb) == "hermes":
            # PATH hermes — assume present if which succeeds
            import shutil

            found = shutil.which("hermes")
            hermes_ok = bool(found)
            hermes_detail = found or "hermes not on PATH"
    except Exception as exc:
        hermes_detail = str(exc)

    status = "ok" if hcx_ok else "degraded"
    return {
        "status": status,
        "version": __version__,
        "stt": {"backend": "faster-whisper", "model": stt.model_size, "loaded": stt.loaded},
        "tts": {
            "backend": "kokoro",
            "voice": tts.voice,
            "loaded": tts.loaded,
            "error": tts.last_error,
        },
        "hcx": {"ok": hcx_ok, "detail": hcx_detail},
        "hermes": {"ok": hermes_ok, "detail": hermes_detail},
        "cursor_key_present": bool(os.environ.get("CURSOR_API_KEY", "").strip()),
    }


@app.post("/stt")
async def stt_endpoint(audio: UploadFile = File(...)) -> dict[str, str]:
    data = await audio.read()
    if not data:
        raise HTTPException(400, "empty audio")
    name = audio.filename or "audio.webm"
    suffix = Path(name).suffix or ".webm"
    try:
        text = get_stt().transcribe_bytes(data, suffix=suffix)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(500, f"STT failed: {exc}") from exc
    return {"text": text}


@app.post("/tts")
async def tts_endpoint(body: TTSRequest) -> Response:
    try:
        wav, _sr = get_tts().synthesize(body.text, voice=body.voice)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(500, f"TTS failed: {exc}") from exc
    return Response(content=wav, media_type="audio/wav")


@app.post("/turn", response_model=TurnResponse)
async def turn_endpoint(audio: UploadFile = File(...)) -> TurnResponse:
    data = await audio.read()
    if not data:
        raise HTTPException(400, "empty audio")
    name = audio.filename or "audio.webm"
    suffix = Path(name).suffix or ".webm"

    try:
        transcript = get_stt().transcribe_bytes(data, suffix=suffix)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(500, f"STT failed: {exc}") from exc

    if not transcript:
        raise HTTPException(400, "could not transcribe speech (empty)")

    try:
        reply = ask_hermes(transcript)
    except Exception as exc:
        logger.exception("Hermes failed")
        raise HTTPException(502, f"Hermes failed: {exc}") from exc

    try:
        wav, _sr = get_tts().synthesize(reply)
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(500, f"TTS failed: {exc}") from exc

    return TurnResponse(
        transcript=transcript,
        reply=reply,
        audio_base64=base64.b64encode(wav).decode("ascii"),
        content_type="audio/wav",
    )


@app.get("/")
def index() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "static UI missing")
    return FileResponse(index_path)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def run(host: str | None = None, port: int | None = None) -> None:
    import uvicorn

    host = host or os.environ.get("HCX_VOICE_HOST", "127.0.0.1")
    port = port or int(os.environ.get("HCX_VOICE_PORT", "8767"))
    # Security: refuse non-loopback unless explicitly allowed
    allow_public = os.environ.get("HCX_VOICE_ALLOW_PUBLIC", "").strip() in ("1", "true")
    if host not in ("127.0.0.1", "localhost", "::1") and not allow_public:
        raise SystemExit(
            f"Refusing to bind {host!r} (loopback only). "
            "Set HCX_VOICE_ALLOW_PUBLIC=1 only behind your own reverse proxy / tunnel."
        )
    uvicorn.run(
        "hcx_voice.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
