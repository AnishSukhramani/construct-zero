"""FastAPI voice sidecar: /health /stt /tts /turn /nav + hold-to-talk UI."""

from __future__ import annotations

import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from hcx_vpl.config import VplConfig
from hcx_vpl.engine import PresentationEngine
from hcx_vpl.intents import is_navigation_intent
from hcx_vpl.models import NavPhase
from pydantic import BaseModel, Field

from hcx_voice import __version__
from hcx_voice.hermes_bridge import ask_hermes, check_hcx_up
from hcx_voice.session_store import SessionStore
from hcx_voice.stt_whisper import WhisperSTT
from hcx_voice.tts_kokoro import KokoroTTS

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

_stt: WhisperSTT | None = None
_tts: KokoroTTS | None = None
_vpl_engine: PresentationEngine | None = None
_session_store: SessionStore | None = None


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


def get_vpl_engine() -> PresentationEngine:
    global _vpl_engine
    if _vpl_engine is None:
        _vpl_engine = PresentationEngine(VplConfig.from_env())
    return _vpl_engine


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        cfg = VplConfig.from_env()
        _session_store = SessionStore(ttl_sec=cfg.session_ttl_sec)
    return _session_store


def set_backends(
    stt: WhisperSTT | None = None,
    tts: KokoroTTS | None = None,
    vpl_engine: PresentationEngine | None = None,
    session_store: SessionStore | None = None,
) -> None:
    """Test hook to inject mock backends."""
    global _stt, _tts, _vpl_engine, _session_store
    if stt is not None:
        _stt = stt
    if tts is not None:
        _tts = tts
    if vpl_engine is not None:
        _vpl_engine = vpl_engine
    if session_store is not None:
        _session_store = session_store


def reset_backends() -> None:
    global _stt, _tts, _vpl_engine, _session_store
    _stt = None
    _tts = None
    _vpl_engine = None
    _session_store = None


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


class NavRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    command: str = Field(..., min_length=1)


class TurnResponse(BaseModel):
    transcript: str
    reply: str
    speak_text: str = ""
    audio_base64: str
    content_type: str = "audio/wav"
    session_id: str | None = None
    mode: str = "passthrough"
    buckets: list[dict[str, Any]] = Field(default_factory=list)
    nav_hint: str = ""


def _synthesize_speech(text: str) -> tuple[bytes, int]:
    return get_tts().synthesize(text)


def _build_turn_response(
    transcript: str,
    *,
    speak_text: str,
    reply: str,
    session_id: str | None,
    mode: str,
    buckets: list[dict[str, Any]],
    nav_hint: str,
) -> TurnResponse:
    wav, _sr = _synthesize_speech(speak_text)
    return TurnResponse(
        transcript=transcript,
        reply=reply,
        speak_text=speak_text,
        audio_base64=base64.b64encode(wav).decode("ascii"),
        content_type="audio/wav",
        session_id=session_id,
        mode=mode,
        buckets=buckets,
        nav_hint=nav_hint,
    )


def _route_transcript(transcript: str, session_id: str | None) -> tuple[str, str, str | None, str, list[dict], str]:
    """Return speak_text, reply, session_id, mode, buckets, nav_hint."""
    engine = get_vpl_engine()
    store = get_session_store()
    session = store.get(session_id)

    if session and session.phase in (NavPhase.WAIT, NavPhase.DEEPEN, NavPhase.MAP):
        if is_navigation_intent(transcript, session.document.buckets):
            updated, result = engine.step(session, transcript)
            if result.mode == "new_question":
                store.delete(session_id)
            elif updated is None:
                store.delete(session.session_id)
            else:
                store.put(updated)
            return (
                result.speak_text,
                result.reply_full,
                result.session_id,
                result.mode,
                result.buckets,
                result.nav_hint,
            )

    reply = ask_hermes(transcript)
    new_session, result = engine.begin(reply, session_id=session_id)
    if new_session is not None:
        store.put(new_session)
    else:
        store.delete(session_id)
    return (
        result.speak_text,
        result.reply_full,
        result.session_id,
        result.mode,
        result.buckets,
        result.nav_hint,
    )


def _run_nav_command(session_id: str, command: str) -> TurnResponse:
    store = get_session_store()
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "session not found or expired")

    engine = get_vpl_engine()
    updated, result = engine.step(session, command)
    if result.mode == "new_question":
        store.delete(session_id)
        raise HTTPException(400, "command is not a navigation intent")
    if updated is None:
        store.delete(session_id)
    else:
        store.put(updated)

    wav, _sr = _synthesize_speech(result.speak_text)
    return TurnResponse(
        transcript=command,
        reply=result.reply_full,
        speak_text=result.speak_text,
        audio_base64=base64.b64encode(wav).decode("ascii"),
        content_type="audio/wav",
        session_id=result.session_id,
        mode=result.mode,
        buckets=result.buckets,
        nav_hint=result.nav_hint,
    )


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
            import shutil

            found = shutil.which("hermes")
            hermes_ok = bool(found)
            hermes_detail = found or "hermes not on PATH"
    except Exception as exc:
        hermes_detail = str(exc)

    vpl_cfg = VplConfig.from_env()
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
        "vpl": {"enabled": vpl_cfg.enabled, "layer_threshold_items": vpl_cfg.layer_threshold_items},
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


@app.post("/nav", response_model=TurnResponse)
async def nav_endpoint(body: NavRequest) -> TurnResponse:
    try:
        return _run_nav_command(body.session_id, body.command)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Nav failed")
        raise HTTPException(500, f"Nav failed: {exc}") from exc


@app.post("/turn", response_model=TurnResponse)
async def turn_endpoint(
    audio: UploadFile = File(...),
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
) -> TurnResponse:
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
        speak_text, reply, session_id, mode, buckets, nav_hint = _route_transcript(
            transcript, x_session_id
        )
    except Exception as exc:
        logger.exception("Turn routing failed")
        raise HTTPException(502, f"Turn failed: {exc}") from exc

    try:
        return _build_turn_response(
            transcript,
            speak_text=speak_text,
            reply=reply,
            session_id=session_id,
            mode=mode,
            buckets=buckets,
            nav_hint=nav_hint,
        )
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(500, f"TTS failed: {exc}") from exc


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
