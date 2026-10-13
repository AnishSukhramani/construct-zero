"""CursorDriver unit tests with fake cursor_sdk."""

from __future__ import annotations

import threading
import time

import cursor_sdk
import pytest
from construct_zero.config import CursorDriverConfig, CZConfig, InferenceConfig, load_config
from construct_zero.core.sessions import SessionStore
from construct_zero.drivers.cursor import (
    ActiveRun,
    CursorDriver,
    _message_text,
    _openai_tool_schema,
    messages_to_prompt,
)
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage


def _driver(**kwargs) -> CursorDriver:
    cfg = CZConfig(
        inference=InferenceConfig(
            model="auto",
            cursor=CursorDriverConfig(
                mode="ask",
                workspace_isolation=False,
                api_key_env="CURSOR_API_KEY",
            ),
        )
    )
    return CursorDriver(cfg, SessionStore(), tool_wait_timeout=2.0)


def test_message_text_and_prompt():
    assert _message_text(None) == ""
    assert _message_text([{"type": "text", "text": "hi"}]) == "hi"
    prompt = messages_to_prompt(
        [
            ChatMessage(role="system", content="sys"),
            ChatMessage(role="user", content="u"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[{"id": "c1", "type": "function", "function": {"name": "t"}}],
            ),
            ChatMessage(role="tool", content='{"ok":true}', tool_call_id="c1"),
        ]
    )
    assert "[system]" in prompt
    assert "[user]" in prompt
    assert "tool_calls" in prompt
    assert "[tool_result" in prompt


def test_openai_tool_schema_variants():
    name, desc, params = _openai_tool_schema(
        {"type": "function", "function": {"name": "fn", "description": "d", "parameters": {}}}
    )
    assert name == "fn"
    assert desc == "d"
    name2, _, _ = _openai_tool_schema({"name": "legacy", "parameters": {"type": "object"}})
    assert name2 == "legacy"


def test_active_run_batch():
    from construct_zero.core.sessions import ToolLoopSession

    session = ToolLoopSession(session_id="s")
    active = ActiveRun(session=session)
    active.push_tool({"id": "a", "type": "function", "function": {}})
    batch = active.take_batch()
    assert len(batch) == 1
    assert active.take_batch() == []


def test_health_missing_key(monkeypatch):
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    drv = _driver()
    h = drv.health()
    assert h.ok is False
    assert "CURSOR_API_KEY" in h.detail


def test_health_wrong_mode(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cfg = CZConfig()
    cfg.inference.cursor.mode = "agent"
    cfg.inference.cursor.workspace_isolation = False
    drv = CursorDriver(cfg)
    assert drv.health().ok is False


def test_health_sdk_ok(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    drv = _driver()
    h = drv.health()
    assert h.ok is True


def test_health_sdk_failure(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk._ModelsAPI.list_fail = RuntimeError("boom")
    drv = _driver()
    assert drv.health().ok is False


def test_list_models_fallback_and_success(monkeypatch):
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    drv = _driver()
    assert "auto" in drv.list_models()
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk._ModelsAPI.models = [cursor_sdk.Model("composer-2.5")]
    ids = drv.list_models()
    assert ids[0] == "auto"


def test_complete_text(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.default_text = "hello there"
    drv = _driver()
    req = ChatCompletionRequest(messages=[ChatMessage(role="user", content="hi")])
    out = drv.complete(req)
    assert out.text == "hello there"
    assert out.finish_reason == "stop"


def test_complete_text_error_status(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.default_status = "error"
    cursor_sdk.Agent.default_error = cursor_sdk.RunError(message="bad run")
    drv = _driver()
    with pytest.raises(RuntimeError, match="bad run"):
        drv.complete(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        )


def test_complete_missing_key():
    drv = _driver()
    with pytest.raises(RuntimeError, match="CURSOR_API_KEY"):
        drv.complete(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        )


def test_stream_text_chunks(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.stream_chunks = ["chunk-a", "chunk-b"]
    cursor_sdk.Agent.default_text = "chunk-a" + "chunk-b"
    drv = _driver()
    chunks = list(
        drv.stream(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        )
    )
    assert chunks[-1].done is True
    pieces = [
        c.data.get("choices", [{}])[0].get("delta", {}).get("content")
        for c in chunks
        if c.data.get("choices")
    ]
    assert "chunk-a" in pieces
    assert "chunk-b" in pieces


def test_stream_emits_before_wait_finishes(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.stream_chunks = ["early"]
    gate = threading.Event()

    def slow_wait(prompt: str, options: cursor_sdk.AgentOptions | None) -> None:
        gate.wait(timeout=2)

    cursor_sdk.Agent.wait_hook = slow_wait
    drv = _driver()
    gen = drv.stream(
        ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
    )
    first = next(gen)
    assert first.data["choices"][0]["delta"].get("content") == ""
    second = next(gen)
    assert second.data["choices"][0]["delta"].get("content") == "early"
    gate.set()
    list(gen)


def test_complete_populates_usage(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.run_usage = cursor_sdk.TokenUsage(
        input_tokens=10, output_tokens=5, total_tokens=15, cache_read_tokens=0, cache_write_tokens=0
    )
    cursor_sdk.Agent.default_text = "ok"
    out = _driver().complete(
        ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
    )
    assert out.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert not (out.raw or {}).get("usage_estimated")


def test_stream_without_iter_text_fallback(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    cursor_sdk.Agent.stream_chunks = []
    cursor_sdk.Agent.default_text = "fallback-text"

    class RunNoIter:
        def wait(self):
            return cursor_sdk.RunOutcome(result="fallback-text")

        def text(self):
            return "fallback-text"

    class Ctx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def send(self, prompt):
            return RunNoIter()

    cursor_sdk.Agent.create_factory = lambda p, o: RunNoIter()
    monkeypatch.setattr(cursor_sdk.Agent, "create", lambda options: Ctx())
    chunks = list(
        _driver().stream(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        )
    )
    assert any(
        (c.data.get("choices") or [{}])[0].get("delta", {}).get("content") == "fallback-text"
        for c in chunks
    )


def test_tool_timeout_from_config(monkeypatch):
    monkeypatch.setenv("CZ_TOOL_TIMEOUT_S", "42")
    cfg = load_config()
    drv = CursorDriver(cfg, SessionStore())
    assert drv._tool_wait_timeout == 42.0


def test_stream_tool_calls(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    drv = _driver()
    req = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="run")],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "terminal",
                    "description": "shell",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    def deliver_tool(prompt: str, options: cursor_sdk.AgentOptions | None) -> None:
        time.sleep(0.05)

    cursor_sdk.Agent.wait_hook = deliver_tool
    cursor_sdk.Agent.invoke_tools_on_send = True

    result_holder: list = []

    def run_complete():
        result_holder.append(drv.complete(req))

    t = threading.Thread(target=run_complete)
    t.start()
    time.sleep(0.15)
    # Tool run should park — complete may return tool_calls
    t.join(timeout=3)
    assert result_holder


def test_resume_with_tool_results(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "k")
    store = SessionStore()
    drv = CursorDriver(
        CZConfig(inference=InferenceConfig(cursor=CursorDriverConfig(workspace_isolation=False))),
        store,
        tool_wait_timeout=2.0,
    )
    session = store.create()
    active = ActiveRun(session=session, model="auto")
    tc = {
        "id": "call_resume",
        "type": "function",
        "function": {"name": "t", "arguments": "{}"},
    }
    active.push_tool(tc)
    drv._runs[session.session_id] = active
    drv._call_to_run["call_resume"] = session.session_id

    def unblock():
        time.sleep(0.05)
        active.session.deliver_result("call_resume", '{"ok":1}')
        active.done_event.set()
        active.final_text = "done"

    threading.Thread(target=unblock, daemon=True).start()
    out = drv.complete(
        ChatCompletionRequest(
            messages=[
                ChatMessage(role="tool", content='{"ok":1}', tool_call_id="call_resume")
            ]
        )
    )
    assert out.text == "done" or out.tool_calls
