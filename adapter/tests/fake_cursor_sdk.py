"""In-process stand-in for cursor_sdk (no network, no API keys)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Model:
    id: str


class _ModelsAPI:
    list_fail: BaseException | None = None
    models: list[Model] = field(default_factory=lambda: [Model("auto"), Model("composer-2.5")])

    @classmethod
    def list(cls, api_key: str | None = None) -> list[Model]:
        if cls.list_fail is not None:
            raise cls.list_fail
        return list(cls.models)


class Cursor:
    models = _ModelsAPI


@dataclass
class LocalAgentOptions:
    cwd: str = ""
    custom_tools: dict[str, Any] | None = None


@dataclass
class AgentOptions:
    model: str = "auto"
    api_key: str = ""
    tools: list[Any] = field(default_factory=list)
    mode: str = "ask"
    local: LocalAgentOptions | None = None


@dataclass
class RunError:
    message: str = "error"


@dataclass
class RunOutcome:
    status: str = "finished"
    result: str = ""
    error: RunError | None = None


@dataclass
class _ToolContext:
    tool_call_id: str = "call_fake_1"


class AgentRun:
    def __init__(self, options: AgentOptions | None = None) -> None:
        self._options = options
        self._prompt = ""
        self._tools_invoked = False

    def send(self, prompt: str) -> AgentRun:
        self._prompt = prompt
        return self

    def _invoke_custom_tools(self) -> None:
        if self._tools_invoked or not self._options or not self._options.local:
            return
        tools = self._options.local.custom_tools or {}
        seen: set[str] = set()
        for name, tool in tools.items():
            if name in seen:
                continue
            seen.add(name)
            execute = getattr(tool, "execute", None)
            if execute is None:
                continue
            execute({"arg": "v"}, _ToolContext(tool_call_id=f"call_{name}"))
        self._tools_invoked = True

    def wait(self) -> RunOutcome:
        if Agent.invoke_tools_on_send:
            self._invoke_custom_tools()
        if Agent.wait_hook is not None:
            Agent.wait_hook(self._prompt, self._options)
        return RunOutcome(
            status=Agent.default_status,
            result=Agent.default_text,
            error=Agent.default_error,
        )

    def text(self) -> str:
        if Agent.text_raises:
            raise Agent.text_raises
        return Agent.default_text


class _AgentContext:
    def __init__(self, options: AgentOptions) -> None:
        self._options = options
        self._run = AgentRun(options=options)

    def __enter__(self) -> _AgentContext:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def send(self, prompt: str) -> AgentRun:
        if Agent.create_factory is not None:
            return Agent.create_factory(prompt, self._options)
        return self._run.send(prompt)


class CustomTool:
    def __init__(
        self,
        *,
        description: str = "",
        input_schema: dict[str, Any] | None = None,
        execute: Callable[..., str] | None = None,
    ) -> None:
        self.description = description
        self.input_schema = input_schema or {}
        self.execute = execute


class Agent:
    create_factory: Callable[[str, AgentOptions], AgentRun] | None = None
    wait_hook: Callable[[str, AgentOptions | None], None] | None = None
    default_text: str = "assistant reply"
    default_status: str = "finished"
    default_error: RunError | None = None
    invoke_tools_on_send: bool = True
    text_raises: BaseException | None = None
    create_lock = threading.Lock()

    @classmethod
    def create(cls, options: AgentOptions) -> _AgentContext:
        return _AgentContext(options)

    @classmethod
    def reset(cls) -> None:
        cls.create_factory = None
        cls.wait_hook = None
        cls.default_text = "assistant reply"
        cls.default_status = "finished"
        cls.default_error = None
        cls.invoke_tools_on_send = True
        cls.text_raises = None
        _ModelsAPI.list_fail = None
        _ModelsAPI.models = [Model("auto"), Model("composer-2.5")]
