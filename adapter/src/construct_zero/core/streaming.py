"""SSE helpers for OpenAI chat.completion.chunk streams."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Iterator


def completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def sse_line(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        return f"data: {payload}\n\n"
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def text_stream_chunks(
    *,
    model: str,
    text: str,
    chunk_chars: int = 48,
) -> Iterator[str]:
    cid = completion_id()
    created = int(time.time())
    yield sse_line(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }
    )
    for i in range(0, max(len(text), 1), chunk_chars):
        piece = text[i : i + chunk_chars]
        if not piece and text:
            continue
        yield sse_line(
            {
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": piece}, "finish_reason": None}
                ],
            }
        )
    yield sse_line(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield sse_line("[DONE]")


def tool_call_stream(
    *,
    model: str,
    tool_calls: list[dict[str, Any]],
) -> Iterator[str]:
    cid = completion_id()
    created = int(time.time())
    yield sse_line(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": None, "tool_calls": tool_calls},
                    "finish_reason": None,
                }
            ],
        }
    )
    yield sse_line(
        {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
        }
    )
    yield sse_line("[DONE]")
