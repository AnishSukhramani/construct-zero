"""CursorDriver — Cursor subscription inference via cursor-sdk.

Phase 1: text chat (tools=[] so Cursor does not run its own tools).
Phase 2: Hermes tools as SDK custom_tools; park/resume via ActiveRun so Hermes
executes tools while Cursor only reasons.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from construct_zero.config import CursorDriverConfig, CZConfig
from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.core.sessions import SessionStore, ToolLoopSession
from construct_zero.core.streaming import completion_id
from construct_zero.drivers.acp import check_acp
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage

logger = logging.getLogger(__name__)


def _message_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif isinstance(block, dict) and "text" in block:
            parts.append(str(block["text"]))
    return "\n".join(parts)


def messages_to_prompt(messages: list[ChatMessage]) -> str:
    lines: list[str] = []
    for msg in messages:
        role = msg.role
        text = _message_text(msg.content)
        if role == "system":
            lines.append(f"[system]\n{text}")
        elif role == "user":
            lines.append(f"[user]\n{text}")
        elif role == "assistant":
            if msg.tool_calls:
                lines.append(
                    f"[assistant tool_calls]\n{json.dumps(msg.tool_calls, ensure_ascii=False)}"
                )
            if text:
                lines.append(f"[assistant]\n{text}")
        elif role == "tool":
            tid = msg.tool_call_id or "unknown"
            lines.append(f"[tool_result id={tid}]\n{text}")
        else:
            lines.append(f"[{role}]\n{text}")
    lines.append(
        "\n[instruction]\nRespond as the assistant. "
        "If tools are available, call them via the provided custom tools rather than inventing results."
    )
    return "\n\n".join(lines)


def _openai_tool_schema(tool: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
        fn = tool["function"]
        return (
            str(fn.get("name") or "tool"),
            str(fn.get("description") or ""),
            fn.get("parameters") or {"type": "object", "properties": {}},
        )
    return (
        str(tool.get("name") or "tool"),
        str(tool.get("description") or ""),
        tool.get("parameters")
        or tool.get("input_schema")
        or {"type": "object", "properties": {}},
    )


@dataclass
class ActiveRun:
    """Background Cursor agent run waiting on Hermes tool results."""

    session: ToolLoopSession
    batch_tools: list[dict[str, Any]] = field(default_factory=list)
    batch_event: threading.Event = field(default_factory=threading.Event)
    batch_lock: threading.Lock = field(default_factory=threading.Lock)
    done_event: threading.Event = field(default_factory=threading.Event)
    final_text: str = ""
    error: BaseException | None = None
    model: str = "auto"

    def push_tool(self, tc: dict[str, Any]) -> None:
        with self.batch_lock:
            self.batch_tools.append(tc)
            self.batch_event.set()

    def take_batch(self) -> list[dict[str, Any]]:
        with self.batch_lock:
            tools = list(self.batch_tools)
            self.batch_tools.clear()
            self.batch_event.clear()
            return tools


class CursorDriver:
    name = "cursor"

    def __init__(self, config: CZConfig, sessions: SessionStore | None = None) -> None:
        self.config = config
        self.cursor_cfg: CursorDriverConfig = config.inference.cursor
        self.sessions = sessions or SessionStore()
        self._workspace = self._make_workspace()
        self._acp = check_acp(self.cursor_cfg.agent_bin)
        self._runs: dict[str, ActiveRun] = {}
        self._runs_lock = threading.Lock()
        self._call_to_run: dict[str, str] = {}

    def _make_workspace(self) -> str:
        if self.cursor_cfg.workspace_isolation:
            return tempfile.mkdtemp(prefix="construct-zero-cursor-ws-")
        return os.getcwd()

    def _api_key(self) -> str:
        return self.config.cursor_api_key()

    def _resolve_model(self, requested: str | None) -> str:
        return (requested or self.config.inference.model or "auto").strip() or "auto"

    def health(self) -> HealthStatus:
        key = self._api_key()
        if not key:
            return HealthStatus(
                ok=False,
                detail=f"Missing {self.cursor_cfg.api_key_env}. Export your Cursor API key.",
            )
        if self.cursor_cfg.mode != "ask":
            return HealthStatus(
                ok=False,
                detail=f"cursor.mode must be 'ask' (got {self.cursor_cfg.mode!r})",
            )
        try:
            from cursor_sdk import Cursor

            models = Cursor.models.list(api_key=key)
            count = len(models) if models is not None else 0
            return HealthStatus(
                ok=True,
                detail=(
                    f"cursor-sdk ok; {count} models; workspace={self._workspace}; "
                    f"{self._acp.detail}"
                ),
            )
        except Exception as exc:
            return HealthStatus(ok=False, detail=f"cursor-sdk health failed: {exc}")

    def list_models(self) -> list[str]:
        key = self._api_key()
        fallback = ["auto", "composer-2.5", "composer-2.5-fast"]
        if not key:
            return fallback
        try:
            from cursor_sdk import Cursor

            models = Cursor.models.list(api_key=key)
            ids = [m.id for m in models if getattr(m, "id", None)]
            if "auto" not in ids:
                ids.insert(0, "auto")
            return ids or fallback
        except Exception as exc:
            logger.warning("list_models failed: %s", exc)
            return fallback

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        model = self._resolve_model(request.model)
        tool_results = self._extract_tool_results(request.messages)
        if tool_results:
            resumed = self._resume_with_tool_results(tool_results, model)
            if resumed is not None:
                return resumed
        if request.tools:
            return self._start_tool_run(request, model)
        return self._complete_text(request, model)

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        result = self.complete(request)
        cid = completion_id()
        created = int(time.time())
        if result.tool_calls:
            yield StreamChunk(
                data={
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": result.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "index": i,
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": tc["function"],
                                    }
                                    for i, tc in enumerate(result.tool_calls)
                                ],
                            },
                            "finish_reason": None,
                        }
                    ],
                }
            )
            yield StreamChunk(
                data={
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": result.model,
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "tool_calls"}
                    ],
                },
                done=True,
            )
            return

        text = result.text or ""
        yield StreamChunk(
            data={
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": result.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None,
                    }
                ],
            }
        )
        step = 64
        for i in range(0, max(len(text), 1), step):
            piece = text[i : i + step]
            if not piece:
                continue
            yield StreamChunk(
                data={
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": result.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
            )
        yield StreamChunk(
            data={
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": result.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
            done=True,
        )

    def _extract_tool_results(
        self, messages: list[ChatMessage]
    ) -> list[tuple[str, str]]:
        return [
            (m.tool_call_id, _message_text(m.content))
            for m in messages
            if m.role == "tool" and m.tool_call_id
        ]

    def _agent_options(
        self,
        *,
        model: str,
        api_key: str,
        custom_tools: dict[str, Any] | None = None,
    ):
        """Build AgentOptions for cursor-sdk 1.x (tools live on options, not create kwargs)."""
        from cursor_sdk import AgentOptions, LocalAgentOptions

        local_kwargs: dict[str, Any] = {"cwd": self._workspace}
        if custom_tools is not None:
            local_kwargs["custom_tools"] = custom_tools
        return AgentOptions(
            model=model,
            api_key=api_key,
            # Empty allowlist = no Cursor built-in tools; Hermes owns tooling.
            tools=[],
            mode="ask",
            local=LocalAgentOptions(**local_kwargs),
        )

    def _complete_text(
        self, request: ChatCompletionRequest, model: str
    ) -> CompletionResult:
        from cursor_sdk import Agent

        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(f"Missing {self.cursor_cfg.api_key_env}")

        prompt = messages_to_prompt(request.messages)
        with Agent.create(self._agent_options(model=model, api_key=api_key)) as agent:
            run = agent.send(prompt)
            result = run.wait()
            text = (result.result if result else None) or ""
            try:
                text = run.text() or text
            except Exception:
                pass
            status = getattr(result, "status", None) or "finished"
            if status == "error":
                err = getattr(result, "error", None)
                msg = getattr(err, "message", None) or str(err) or "cursor run error"
                raise RuntimeError(msg)
            return CompletionResult(text=text, finish_reason="stop", model=model)

    def _wait_outcome(self, active: ActiveRun, timeout: float = 300.0) -> CompletionResult:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if active.batch_event.wait(timeout=0.2):
                time.sleep(0.12)  # coalesce parallel tool calls
                tools = active.take_batch()
                if tools:
                    seen: set[str] = set()
                    unique: list[dict[str, Any]] = []
                    for tc in tools:
                        if tc["id"] in seen:
                            continue
                        seen.add(tc["id"])
                        unique.append(tc)
                        self._call_to_run[tc["id"]] = active.session.session_id
                    return CompletionResult(
                        text="",
                        tool_calls=unique,
                        finish_reason="tool_calls",
                        model=active.model,
                        raw={"cz_session_id": active.session.session_id},
                    )
            if active.done_event.is_set():
                break
        if active.error:
            raise active.error
        return CompletionResult(
            text=active.final_text,
            finish_reason="stop",
            model=active.model,
            raw={"cz_session_id": active.session.session_id},
        )

    def _resume_with_tool_results(
        self, results: list[tuple[str, str]], model: str
    ) -> CompletionResult | None:
        run_id: str | None = None
        for call_id, content in results:
            rid = self._call_to_run.get(call_id)
            if rid:
                run_id = rid
            with self._runs_lock:
                active = self._runs.get(rid) if rid else None
            if active:
                active.session.deliver_result(call_id, content)
            else:
                # Best-effort scan
                for a in list(self._runs.values()):
                    if a.session.deliver_result(call_id, content):
                        run_id = a.session.session_id
                        break

        if not run_id:
            return None
        with self._runs_lock:
            active = self._runs.get(run_id)
        if not active:
            return None
        active.model = model or active.model
        return self._wait_outcome(active)

    def _start_tool_run(
        self, request: ChatCompletionRequest, model: str
    ) -> CompletionResult:
        from cursor_sdk import Agent, CustomTool

        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(f"Missing {self.cursor_cfg.api_key_env}")

        session = self.sessions.create()
        active = ActiveRun(session=session, model=model)
        with self._runs_lock:
            self._runs[session.session_id] = active

        def make_tool(name: str, description: str, parameters: dict[str, Any]) -> CustomTool:
            def execute(args: dict[str, Any], context: Any = None) -> str:
                call_id = None
                if context is not None:
                    call_id = getattr(context, "tool_call_id", None)
                arguments = json.dumps(
                    args if isinstance(args, dict) else {"value": args},
                    ensure_ascii=False,
                )
                pending = session.park(
                    name=name, arguments=arguments, call_id=call_id
                )
                tc = {
                    "id": pending.call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
                active.push_tool(tc)
                return session.wait_result(pending.call_id, timeout=300.0)

            return CustomTool(
                description=description or f"Hermes tool {name}",
                input_schema=parameters,
                execute=execute,
            )

        custom_tools: dict[str, Any] = {}
        for tool in request.tools or []:
            name, desc, params = _openai_tool_schema(tool)
            if not name:
                continue
            safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
            custom_tools[safe] = make_tool(name, desc, params)
            if safe != name:
                custom_tools[name] = custom_tools[safe]

        prompt = messages_to_prompt(request.messages)
        options = self._agent_options(
            model=model, api_key=api_key, custom_tools=custom_tools
        )

        def runner() -> None:
            try:
                with Agent.create(options) as agent:
                    run = agent.send(prompt)
                    result = run.wait()
                    text = (result.result if result else None) or ""
                    try:
                        text = run.text() or text
                    except Exception:
                        pass
                    active.final_text = text
                    status = getattr(result, "status", None)
                    if status == "error":
                        err = getattr(result, "error", None)
                        active.error = RuntimeError(
                            getattr(err, "message", None)
                            or str(err)
                            or "run error"
                        )
            except BaseException as exc:
                active.error = exc
            finally:
                active.batch_event.set()
                active.done_event.set()
                session.close()

        threading.Thread(
            target=runner,
            name=f"construct-zero-cursor-{session.session_id}",
            daemon=True,
        ).start()

        return self._wait_outcome(active)
