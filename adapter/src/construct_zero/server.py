"""FastAPI OpenAI-compatible server for Construct-Zero."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Iterator
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from construct_zero import __version__
from construct_zero.config import CZConfig, load_config
from construct_zero.core.backend import CompletionResult
from construct_zero.core.sessions import SessionStore
from construct_zero.core.streaming import sse_line
from construct_zero.drivers.claude_code import ClaudeCodeDriver
from construct_zero.drivers.cursor import CursorDriver
from construct_zero.drivers.mock import MockDriver
from construct_zero.home import admin as cz_admin
from construct_zero.home import identity as cz_identity
from construct_zero.home import inference_guard as cz_guard
from construct_zero.home import kill_registry as cz_kill_registry
from construct_zero.home import ledger as cz_ledger
from construct_zero.home import registry as cz_registry
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
    app.state.cz_ledger_path = None  # tests may override
    app.state.cz_budgets_path = None
    cz_ledger.init_db(app.state.cz_ledger_path)
    cz_admin.ensure_admin_key()

    @app.exception_handler(HTTPException)
    async def openai_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code = "cz_error"
        if exc.status_code == 401:
            code = "cz_auth_missing" if "Missing" in detail else "cz_auth_invalid"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": detail,
                    "type": "invalid_request_error",
                    "code": code,
                },
                "detail": detail,
            },
        )

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

    def require_admin(authorization: str | None = Header(default=None)) -> None:
        if not cz_admin.verify_admin_key(authorization):
            raise HTTPException(status_code=401, detail="Invalid admin key")

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
        return ModelsListResponse(data=[ModelCard(id=mid, created=now) for mid in ids])

    @app.post("/v1/chat/completions", dependencies=[Depends(require_auth)])
    def chat_completions(
        body: ChatCompletionRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        b = request.app.state.backend
        if body.tools and b.name == "claude_code":
            raise HTTPException(
                status_code=501,
                detail="Tools not supported on claude_code stub",
            )

        killed = cz_guard.check_killed()
        if killed:
            return JSONResponse(status_code=503, content=killed)

        headers = {k.lower(): v for k, v in request.headers.items()}
        agent, hdr_session = cz_identity.resolve_agent(headers, body, authorization)
        session = cz_identity.session_id_from_request(agent, body, hdr_session)
        prompt_est = cz_guard.estimate_prompt_tokens(body)
        db_path = request.app.state.cz_ledger_path
        bud_path = request.app.state.cz_budgets_path
        budget_err = cz_guard.check_budget(
            agent, session, prompt_est, budgets_path=bud_path, db_path=db_path
        )
        if budget_err:
            if body.stream:
                return StreamingResponse(
                    _budget_stream(budget_err),
                    media_type="text/event-stream",
                )
            return JSONResponse(status_code=429, content=budget_err)

        req_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        try:
            if body.stream:
                return StreamingResponse(
                    _stream_response(
                        b,
                        body,
                        agent=agent,
                        session=session,
                        request_id=req_id,
                        prompt_est=prompt_est,
                        db_path=db_path,
                    ),
                    media_type="text/event-stream",
                )
            result = b.complete(body)
            completion_est = cz_identity.estimate_tokens(result.text or "")
            cz_guard.record_adapter_usage(
                agent=agent,
                session=session,
                model=result.model or body.model,
                prompt_tokens=prompt_est,
                completion_tokens=completion_est,
                request_id=req_id,
                status=200,
                db_path=db_path,
            )
            return _to_openai_response(result, body.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("chat.completions failed")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/cz/v1/usage", dependencies=[Depends(require_admin)])
    def cz_usage(
        request: Request,
        since: str | None = None,
        until: str | None = None,
        group_by: str = "agent",
    ):
        rows = cz_ledger.aggregate_usage(
            since=since,
            until=until,
            group_by=group_by,
            db_path=request.app.state.cz_ledger_path,
        )
        return {"data": rows}

    @app.get("/cz/v1/agents", dependencies=[Depends(require_admin)])
    def cz_agents():
        reg = cz_registry.sync_registry()
        return reg.to_dict()

    @app.post("/cz/v1/admin/kill", dependencies=[Depends(require_admin)])
    def cz_kill(request: Request, reason: str = ""):
        cz_admin.set_killed(reason)
        request.app.state.sessions.close_all()
        cz_kill_registry.terminate_all()
        return {"status": "killed"}

    @app.post("/cz/v1/admin/unkill", dependencies=[Depends(require_admin)])
    def cz_unkill():
        cz_admin.clear_killed()
        return {"status": "ok"}

    return app


def _build_backend(config: CZConfig, sessions: SessionStore):
    backend_name = (config.inference.backend or "cursor").strip().lower()
    if backend_name in {"cursor", "hcx", "construct-zero", "cz"}:
        return CursorDriver(config, sessions=sessions)
    if backend_name == "mock":
        return MockDriver(sessions=sessions)
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
        choices=[ChatCompletionChoice(index=0, message=message, finish_reason=finish)],
        usage=result.usage,
    )


def _budget_stream(err: dict[str, Any]) -> Iterator[str]:
    yield sse_line({"error": err.get("error") or err})
    yield sse_line("[DONE]")


def _stream_response(
    backend,
    body: ChatCompletionRequest,
    *,
    agent: str,
    session: str | None,
    request_id: str,
    prompt_est: int,
    db_path,
) -> Iterator[str]:
    completion_text = ""
    try:
        for chunk in backend.stream(body):
            yield sse_line(chunk.data)
            if chunk.done:
                yield sse_line("[DONE]")
                cz_guard.record_adapter_usage(
                    agent=agent,
                    session=session,
                    model=body.model,
                    prompt_tokens=prompt_est,
                    completion_tokens=cz_identity.estimate_tokens(completion_text),
                    request_id=request_id,
                    status=200,
                    db_path=db_path,
                )
                return
            choices = chunk.data.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                completion_text += delta.get("content") or ""
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
