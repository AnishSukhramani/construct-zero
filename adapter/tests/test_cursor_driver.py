"""CursorDriver unit tests with fake cursor_sdk."""

from __future__ import annotations

import threading
import time

import cursor_sdk
import pytest
from construct_zero.config import CursorDriverConfig, CZConfig, InferenceConfig
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
    cursor_sdk.Agent.default_text = "a" * 100
    drv = _driver()
    chunks = list(
        drv.stream(
            ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")])
        )
    )
    assert chunks[-1].done is True
    assert any(
        c.data.get("choices", [{}])[0].get("delta", {}).get("content")
        for c in chunks
    )


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
