"""Backend placeholder when optional deps are missing."""

from __future__ import annotations

from collections.abc import Iterator

from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.openai_types import ChatCompletionRequest


class StubBackend:
    def __init__(self, *, name: str, detail: str) -> None:
        self.name = name
        self._detail = detail

    def health(self) -> HealthStatus:
        return HealthStatus(ok=False, detail=self._detail)

    def list_models(self) -> list[str]:
        return []

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        raise RuntimeError(self._detail)

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        raise RuntimeError(self._detail)
        yield StreamChunk(data={})  # pragma: no cover
