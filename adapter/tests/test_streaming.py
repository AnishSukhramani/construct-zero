"""Unit tests for SSE streaming helpers."""

from __future__ import annotations

import json

from construct_zero.core.streaming import (
    completion_id,
    sse_line,
    text_stream_chunks,
    tool_call_stream,
)


def test_completion_id_prefix():
    cid = completion_id()
    assert cid.startswith("chatcmpl-")
    assert len(cid) > len("chatcmpl-")


def test_sse_line_json_and_done():
    assert sse_line("[DONE]") == "data: [DONE]\n\n"
    payload = {"object": "chat.completion.chunk", "choices": []}
    line = sse_line(payload)
    assert line.startswith("data: ")
    assert json.loads(line.removeprefix("data: ").strip()) == payload


def test_text_stream_chunks_empty_and_content():
    chunks = list(text_stream_chunks(model="auto", text="", chunk_chars=8))
    assert chunks[0].startswith("data: ")
    assert chunks[-1] == "data: [DONE]\n\n"
    body = list(text_stream_chunks(model="m", text="hello world", chunk_chars=5))
    assert body[-1] == "data: [DONE]\n\n"
    joined = "".join(
        json.loads(c.removeprefix("data: ").strip())["choices"][0]["delta"].get("content", "")
        for c in body
        if c != "data: [DONE]\n\n"
    )
    assert "hello" in joined


def test_tool_call_stream_finish_reason():
    tcs = [
        {
            "index": 0,
            "id": "call_1",
            "type": "function",
            "function": {"name": "x", "arguments": "{}"},
        }
    ]
    chunks = list(tool_call_stream(model="auto", tool_calls=tcs))
    assert len(chunks) == 3
    last = json.loads(chunks[-2].removeprefix("data: ").strip())
    assert last["choices"][0]["finish_reason"] == "tool_calls"
