"""Deterministic mock inference backend for tests and first-run (not for production)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.core.sessions import SessionStore
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage


class MockDriver:
    name = "mock"

    def __init__(self, sessions: SessionStore | None = None) -> None:
        self._sessions = sessions or SessionStore()

    def health(self) -> HealthStatus:
        return HealthStatus(
            ok=True,
            detail="mock backend: for tests and first-run checks, no inference",
        )

    def list_models(self) -> list[str]:
        return ["mock-model", "auto"]

    def _last_user_text(self, request: ChatCompletionRequest) -> str:
        for msg in reversed(request.messages):
            if msg.role == "user" and msg.content:
                return str(msg.content)
            if msg.role == "tool" and msg.content:
                return str(msg.content)
        return ""

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        text = self._last_user_text(request)
        if request.tools:
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            return CompletionResult(
                text="",
                tool_calls=[
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": request.tools[0].function.name,
                            "arguments": json.dumps({"echo": text}),
                        },
                    }
                ],
                finish_reason="tool_calls",
                model=request.model or "mock-model",
            )
        if any(m.role == "tool" for m in request.messages):
            return CompletionResult(
                text=f"mock-resume:{text}",
                finish_reason="stop",
                model=request.model or "mock-model",
            )
        return CompletionResult(
            text=f"mock:{text}",
            finish_reason="stop",
            model=request.model or "mock-model",
        )

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        full = self.complete(request)
        payload = full.text or ""
        chunk_size = 16
        idx = 0
        for i in range(0, max(len(payload), 1), chunk_size):
            piece = payload[i : i + chunk_size] or payload
            yield StreamChunk(
                data={
                    "id": f"chatcmpl-mock",
                    "object": "chat.completion.chunk",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
            )
            idx += 1
        yield StreamChunk(
            data={
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
            done=False,
        )
