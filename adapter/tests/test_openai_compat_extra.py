"""Extra openai_compat coverage."""

from __future__ import annotations

import httpx
import pytest
import respx
from construct_zero.config import CZConfig, InferenceConfig, OpenAICompatConfig
from construct_zero.drivers.openai_compat import OpenAICompatDriver


def _cfg(**overrides) -> CZConfig:
    oc = OpenAICompatConfig(base_url="https://llm.example.com/v1", **overrides)
    return CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))


@respx.mock
def test_list_models_from_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "k")
    respx.get("https://llm.example.com/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})
    )
    ids = OpenAICompatDriver(_cfg()).list_models()
    assert ids == ["a", "b"]


def test_health_missing_base_url() -> None:
    oc = OpenAICompatConfig(base_url="")
    cfg = CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))
    assert OpenAICompatDriver(cfg).health().ok is False


def test_static_models_when_configured() -> None:
    cfg = _cfg(models=["only-one"])
    assert OpenAICompatDriver(cfg).list_models() == ["only-one"]


def test_azure_health_requires_key() -> None:
    oc = OpenAICompatConfig(preset="azure", base_url="https://x.azure.com")
    cfg = CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))
    assert OpenAICompatDriver(cfg).health().ok is False


def test_ollama_health_without_key() -> None:
    oc = OpenAICompatConfig(preset="ollama", base_url="http://127.0.0.1:11434/v1")
    cfg = CZConfig(inference=InferenceConfig(backend="openai_compat", openai_compat=oc))
    assert OpenAICompatDriver(cfg).health().ok is True


def test_list_models_upstream_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CZ_OPENAI_COMPAT_API_KEY", "k")

    class BadClient:
        timeout = 1
        verify = True

        def get(self, url, headers=None):
            raise OSError("network")

    drv = OpenAICompatDriver(_cfg())
    drv._client = BadClient()  # noqa: SLF001
    assert drv.list_models() == ["company-default"]
