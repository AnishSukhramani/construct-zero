"""Inference backend protocol — Cursor today, Claude Code later."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol, runtime_checkable

from construct_zero.openai_types import ChatCompletionRequest


@dataclass
class CompletionResult:
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    model: str = "auto"
    usage: dict[str, int] | None = None
    raw: dict[str, Any] | None = None


@dataclass
class StreamChunk:
    """One OpenAI-style stream delta (already shaped for SSE)."""

    data: dict[str, Any]
    done: bool = False


@dataclass
class HealthStatus:
    ok: bool
    detail: str = ""


@runtime_checkable
class InferenceBackend(Protocol):
    name: str

    def health(self) -> HealthStatus: ...

    def list_models(self) -> list[str]: ...

    def complete(self, request: ChatCompletionRequest) -> CompletionResult: ...

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]: ...
