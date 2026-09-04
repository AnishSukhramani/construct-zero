"""Claude Code driver stub — future InferenceBackend."""

from __future__ import annotations

from typing import Iterator

from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.openai_types import ChatCompletionRequest


class ClaudeCodeDriver:
    """Placeholder for a future Claude Code subscription backend."""

    name = "claude_code"

    def health(self) -> HealthStatus:
        return HealthStatus(ok=False, detail="ClaudeCodeDriver is not implemented yet")

    def list_models(self) -> list[str]:
        raise NotImplementedError("ClaudeCodeDriver is not implemented yet")

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        raise NotImplementedError(
            "ClaudeCodeDriver is not implemented yet. Set inference.backend: cursor."
        )

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        raise NotImplementedError("ClaudeCodeDriver is not implemented yet")
