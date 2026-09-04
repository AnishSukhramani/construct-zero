"""FastAPI OpenAI-compatible server for Construct-Zero."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from construct_zero import __version__
from construct_zero.config import CZConfig, load_config
from construct_zero.core.backend import CompletionResult
from construct_zero.core.sessions import SessionStore
from construct_zero.core.streaming import sse_line
from construct_zero.drivers.claude_code import ClaudeCodeDriver
from construct_zero.drivers.cursor import CursorDriver
from construct_zero.openai_types import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    HealthResponse,
    ModelCard,
    ModelsListResponse,
)

logger = logging.getLogger(__name__)


def create_app(config: CZConfig | None = None) -> FastAPI:
    config = config or load_config()
    sessions = SessionStore()
    backend = _build_backend(config, sessions)

    app = FastAPI(title="Construct-Zero Adapter", version=__version__)
    app.state.config = config
    app.state.backend = backend
    app.state.sessions = sessions

    def require_auth(
        authorization: str | None = Header(default=None),
    ) -> None:
        expected = (app.state.config.adapter.api_key or "").strip()
        if not expected:
            return
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        if token != expected:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        b = request.app.state.backend
        cfg: CZConfig = request.app.state.config
        status = b.health()
        return HealthResponse(
            status="ok" if status.ok else "error",
            version=__version__,
            backend=b.name,
            cursor_key_present=bool(cfg.cursor_api_key()),
            detail=status.detail,
        )

    @app.get("/v1/models", response_model=ModelsListResponse, dependencies=[Depends(require_auth)])
    def list_models(request: Request) -> ModelsListResponse:
        ids = request.app.state.backend.list_models()
        now = int(time.time())
        return ModelsListResponse(
            data=[ModelCard(id=mid, created=now) for mid in ids]
        )

    @app.post("/v1/chat/completions", dependencies=[Depends(require_auth)])
    def chat_completions(body: ChatCompletionRequest, request: Request):
        b = request.app.state.backend
        if body.tools and b.name == "claude_code":
            raise HTTPException(
                status_code=501,
                detail="Tools not supported on claude_code stub",
            )

        try:
            if body.stream:
                return StreamingResponse(
                    _stream_response(b, body),
                    media_type="text/event-stream",
                )
            result = b.complete(body)
            return _to_openai_response(result, body.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("chat.completions failed")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


def _build_backend(config: CZConfig, sessions: SessionStore):
    backend_name = (config.inference.backend or "cursor").strip().lower()
    if backend_name in {"cursor", "hcx", "construct-zero", "cz"}:
        return CursorDriver(config, sessions=sessions)
    if backend_name in {"claude_code", "claude-code"}:
        return ClaudeCodeDriver()
    raise ValueError(f"Unknown inference.backend: {backend_name}")


def _to_openai_response(
    result: CompletionResult, requested_model: str | None
) -> ChatCompletionResponse:
    model = result.model or requested_model or "auto"
    if result.tool_calls:
        message: dict[str, Any] = {
            "role": "assistant",
            "content": result.text or None,
            "tool_calls": result.tool_calls,
        }
        finish = "tool_calls"
    else:
        message = {"role": "assistant", "content": result.text or ""}
        finish = result.finish_reason or "stop"

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        created=int(time.time()),
        model=model,
        choices=[
            ChatCompletionChoice(index=0, message=message, finish_reason=finish)
        ],
        usage=result.usage,
    )


def _stream_response(backend, body: ChatCompletionRequest) -> Iterator[str]:
    try:
        for chunk in backend.stream(body):
            yield sse_line(chunk.data)
            if chunk.done:
                yield sse_line("[DONE]")
                return
        yield sse_line("[DONE]")
    except Exception as exc:
        logger.exception("stream failed")
        yield sse_line({"error": {"message": str(exc), "type": "cz_error"}})
        yield sse_line("[DONE]")


def run(host: str | None = None, port: int | None = None, config_path: str | None = None) -> None:
    from pathlib import Path

    import uvicorn

    cfg = load_config(Path(config_path) if config_path else None)
    app = create_app(cfg)
    uvicorn.run(
        app,
        host=host or cfg.adapter.host,
        port=port or cfg.adapter.port,
        log_level="info",
    )
