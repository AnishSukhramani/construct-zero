"""OpenAI-compatible upstream proxy (Azure, vLLM, Ollama, LiteLLM)."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import httpx

from construct_zero.config import CZConfig, OpenAICompatConfig
from construct_zero.core.backend import CompletionResult, HealthStatus, StreamChunk
from construct_zero.core.registry import Capabilities
from construct_zero.core.sessions import SessionStore
from construct_zero.core.streaming import completion_id
from construct_zero.openai_types import ChatCompletionRequest

logger = logging.getLogger(__name__)


class UpstreamError(RuntimeError):
    def __init__(self, status_code: int, host: str, message: str) -> None:
        self.status_code = status_code
        self.host = host
        super().__init__(message)


def _loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _validate_base_url(cfg: OpenAICompatConfig) -> str:
    base = (cfg.base_url or "").strip().rstrip("/")
    if not base:
        raise UpstreamError(503, "upstream", "inference.openai_compat.base_url is not set")
    parsed = urlparse(base)
    if parsed.scheme == "http" and not _loopback_host(parsed.hostname or ""):
        if not cfg.allow_insecure_http:
            raise UpstreamError(
                400,
                parsed.hostname or "upstream",
                "Refusing non-loopback http:// upstream; set allow_insecure_http or use https",
            )
    return base


class OpenAICompatDriver:
    name = "openai_compat"
    capabilities = Capabilities(tools=True, streaming="native", vision=False, usage=True)

    def __init__(self, config: CZConfig, sessions: SessionStore | None = None) -> None:
        self.config = config
        self.ocfg: OpenAICompatConfig = config.inference.openai_compat
        self._sessions = sessions or SessionStore()
        self._client = httpx.Client(
            timeout=self.ocfg.timeout_s,
            follow_redirects=False,
            verify=self.ocfg.ca_bundle or True,
        )

    def _api_key(self) -> str:
        env_name = self.ocfg.api_key_env or "CZ_OPENAI_COMPAT_API_KEY"
        return (os.environ.get(env_name) or "").strip()

    def health(self) -> HealthStatus:
        try:
            base = _validate_base_url(self.ocfg)
        except UpstreamError as exc:
            return HealthStatus(ok=False, detail=str(exc))
        preset = (self.ocfg.preset or "generic").lower()
        if preset != "ollama" and not self._api_key():
            return HealthStatus(
                ok=False,
                detail=f"Set {self.ocfg.api_key_env} for openai_compat upstream auth",
            )
        return HealthStatus(ok=True, detail=f"openai_compat preset={preset} base={base}")

    def list_models(self) -> list[str]:
        if self.ocfg.models:
            return list(self.ocfg.models)
        try:
            base = _validate_base_url(self.ocfg)
            url = f"{base}/models"
            headers = self._request_headers()
            r = self._client.get(url, headers=headers)
            if r.status_code >= 400:
                return ["company-default"]
            data = r.json()
            ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
            return [i for i in ids if i] or ["company-default"]
        except Exception as exc:
            logger.warning("list_models upstream failed: %s", exc)
            return ["company-default"]

    def _request_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **(self.ocfg.extra_headers or {})}
        key = self._api_key()
        preset = (self.ocfg.preset or "generic").lower()
        if preset == "azure":
            if key:
                headers["api-key"] = key
        elif key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _chat_url(self, model: str | None) -> str:
        base = _validate_base_url(self.ocfg)
        preset = (self.ocfg.preset or "generic").lower()
        if preset == "azure":
            deployment = self.ocfg.azure.deployments.get(model or "", model or "default")
            ver = self.ocfg.azure.api_version
            return (
                f"{base}/openai/deployments/{deployment}/chat/completions"
                f"?api-version={ver}"
            )
        return f"{base}/chat/completions"

    def _payload(self, request: ChatCompletionRequest) -> dict[str, Any]:
        body = request.model_dump(exclude_none=True)
        body["stream"] = False
        return body

    def _raise_upstream(self, resp: httpx.Response) -> None:
        host = urlparse(str(resp.request.url)).hostname or "upstream"
        try:
            detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            detail = resp.text or resp.reason_phrase
        raise UpstreamError(resp.status_code, host, f"upstream {host} HTTP {resp.status_code}: {detail}")

    def complete(self, request: ChatCompletionRequest) -> CompletionResult:
        url = self._chat_url(request.model)
        try:
            resp = self._client.post(url, headers=self._request_headers(), json=self._payload(request))
        except httpx.TimeoutException as exc:
            host = urlparse(url).hostname or "upstream"
            raise UpstreamError(504, host, f"upstream timeout contacting {host}") from exc
        if resp.status_code >= 400:
            self._raise_upstream(resp)
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        usage = data.get("usage")
        usage_out = None
        if isinstance(usage, dict):
            usage_out = {
                "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                "completion_tokens": int(usage.get("completion_tokens") or 0),
                "total_tokens": int(usage.get("total_tokens") or 0),
            }
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            return CompletionResult(
                text=msg.get("content") or "",
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason") or "tool_calls",
                model=data.get("model") or request.model or "company-default",
                usage=usage_out,
            )
        return CompletionResult(
            text=msg.get("content") or "",
            finish_reason=choice.get("finish_reason") or "stop",
            model=data.get("model") or request.model or "company-default",
            usage=usage_out,
        )

    def stream(self, request: ChatCompletionRequest) -> Iterator[StreamChunk]:
        url = self._chat_url(request.model)
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        cid = completion_id()
        created = 0
        try:
            with self._client.stream(
                "POST", url, headers=self._request_headers(), json=payload
            ) as resp:
                if resp.status_code >= 400:
                    self._raise_upstream(resp)
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        yield StreamChunk(data={"id": cid}, done=True)
                        return
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    created = int(chunk.get("created") or created or 0)
                    yield StreamChunk(data=chunk)
        except httpx.TimeoutException as exc:
            host = urlparse(url).hostname or "upstream"
            raise UpstreamError(504, host, f"upstream timeout contacting {host}") from exc
        yield StreamChunk(
            data={
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            },
            done=True,
        )
