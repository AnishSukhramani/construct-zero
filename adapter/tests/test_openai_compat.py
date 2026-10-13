"""openai_compat driver with respx-mocked upstream."""

from __future__ import annotations

import logging

import httpx
import pytest
import respx
from construct_zero.config import CZConfig, InferenceConfig, OpenAICompatConfig
from construct_zero.drivers.openai_compat import OpenAICompatDriver, UpstreamError
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage
from construct_zero.server import create_app
from fastapi.testclient import TestClient


def _cfg(oc_overrides: dict | None = None) -> CZConfig:
    data = {"base_url": "https://llm.example.com/v1", "preset": "generic", **(oc_overrides or {})}
    oc = OpenAICompatConfig(**data)
    return CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))


def test_refuse_insecure_remote_http() -> None:
    cfg = _cfg({"base_url": "http://203.0.113.1/v1", "allow_insecure_http": False})
    drv = OpenAICompatDriver(cfg)
    assert drv.health().ok is False


@respx.mock
def test_complete_text_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "secret-key-123")
    route = respx.post("https://llm.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "corp",
                "choices": [{"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
            },
        )
    )
    drv = OpenAICompatDriver(_cfg())
    out = drv.complete(
        ChatCompletionRequest(messages=[ChatMessage(role="user", content="hi")], model="corp")
    )
    assert out.text == "hello"
    assert out.usage == {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}
    assert route.called
    assert route.calls[0].request.headers["Authorization"].endswith("secret-key-123")


@respx.mock
def test_upstream_401_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "k")
    respx.post("https://llm.example.com/v1/chat/completions").mock(return_value=httpx.Response(401, json={}))
    client = TestClient(create_app(_cfg()))
    r = client.post(
        "/v1/chat/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "x"}]},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "cz_upstream_401"
    assert "secret" not in r.text.lower()


@respx.mock
def test_stream_chunk_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "k")

    def _stream(request: httpx.Request):
        lines = [
            'data: {"choices":[{"delta":{"content":"a"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"b"}}]}\n\n',
            "data: [DONE]\n\n",
        ]
        return httpx.Response(200, content="".join(lines))

    respx.post("https://llm.example.com/v1/chat/completions").mock(side_effect=_stream)
    drv = OpenAICompatDriver(_cfg())
    chunks = list(
        drv.stream(
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="s")], model="m", stream=True
            )
        )
    )
    texts = []
    for ch in chunks:
        for choice in ch.data.get("choices") or []:
            texts.append((choice.get("delta") or {}).get("content") or "")
    assert texts[:2] == ["a", "b"]


@respx.mock
def test_timeout_504(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "k")

    def _timeout(request: httpx.Request):
        raise httpx.TimeoutException("slow")

    respx.post("https://llm.example.com/v1/chat/completions").mock(side_effect=_timeout)
    drv = OpenAICompatDriver(_cfg())
    with pytest.raises(UpstreamError) as ei:
        drv.complete(ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")]))
    assert ei.value.status_code == 504


@respx.mock
def test_azure_url_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "azure-key")
    oc = OpenAICompatConfig(
        preset="azure",
        base_url="https://myazure.openai.azure.com",
        azure={"api_version": "2024-10-21", "deployments": {"gpt": "dep-name"}},
    )
    cfg = CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))
    route = respx.post(
        "https://myazure.openai.azure.com/openai/deployments/dep-name/chat/completions"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]},
        )
    )
    OpenAICompatDriver(cfg).complete(
        ChatCompletionRequest(messages=[ChatMessage(role="user", content="x")], model="gpt")
    )
    assert route.called
    assert route.calls[0].request.headers["api-key"] == "azure-key"


def test_key_never_logged(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "super-secret-key")
    with caplog.at_level(logging.ERROR):
        drv = OpenAICompatDriver(_cfg({"base_url": ""}))
        drv.health()
    assert "super-secret-key" not in caplog.text
