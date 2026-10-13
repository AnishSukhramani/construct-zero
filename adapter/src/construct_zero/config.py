"""Load construct-zero.yaml + environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from construct_zero.envcompat import env_cz


def _repo_root() -> Path:
    # adapter/src/construct_zero/config.py -> repo root
    return Path(__file__).resolve().parents[3]


def default_config_paths() -> list[Path]:
    root = _repo_root()
    explicit = env_cz("CONFIG")
    paths: list[Path | None] = [
        Path(explicit).expanduser() if explicit else None,
        Path.home() / ".construct-zero" / "config.yaml",
        root / "config" / "construct-zero.yaml",
        root / "config" / "construct-zero.yaml.example",
        Path.home() / ".hermesxcursor" / "config.yaml",
        root / "config" / "hermesxcursor.yaml",
        root / "config" / "hermesxcursor.yaml.example",
    ]
    return [p for p in paths if p is not None]


class CursorDriverConfig(BaseModel):
    api_key_env: str = "CURSOR_API_KEY"
    mode: str = "ask"
    workspace_isolation: bool = True
    tool_timeout_s: float = 300.0
    # When True, use ACP CLI path for tool-bearing requests if agent binary exists
    prefer_acp_for_tools: bool = True
    agent_bin: str = ""  # empty = auto-detect cursor-agent / agent


class ClaudeCodeDriverConfig(BaseModel):
    enabled: bool = False


class OpenAICompatAzureConfig(BaseModel):
    api_version: str = "2024-10-21"
    deployments: dict[str, str] = Field(default_factory=dict)


class OpenAICompatConfig(BaseModel):
    preset: str = "generic"  # generic | azure | vllm | ollama | litellm
    base_url: str = ""
    api_key_env: str = "CZ_OPENAI_COMPAT_API_KEY"
    models: list[str] = Field(default_factory=list)
    timeout_s: float = 120.0
    extra_headers: dict[str, str] = Field(default_factory=dict)
    azure: OpenAICompatAzureConfig = Field(default_factory=OpenAICompatAzureConfig)
    allow_insecure_http: bool = False
    ca_bundle: str | None = None


class InferenceConfig(BaseModel):
    backend: str = "cursor"
    model: str = "auto"
    routing: bool = False
    cursor: CursorDriverConfig = Field(default_factory=CursorDriverConfig)
    claude_code: ClaudeCodeDriverConfig = Field(default_factory=ClaudeCodeDriverConfig)
    openai_compat: OpenAICompatConfig = Field(default_factory=OpenAICompatConfig)


class AdapterConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    api_key: str = ""


class CZConfig(BaseModel):
    adapter: AdapterConfig = Field(default_factory=AdapterConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)

    def cursor_api_key(self) -> str:
        env_name = self.inference.cursor.api_key_env or "CURSOR_API_KEY"
        return (os.environ.get(env_name) or "").strip()


# Compat alias for one release
HCXConfig = CZConfig


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: Path | None = None) -> CZConfig:
    data: dict[str, Any] = {}
    if path is not None:
        candidates = [path]
    else:
        candidates = default_config_paths()

    for candidate in candidates:
        if candidate.is_file():
            with candidate.open() as f:
                loaded = yaml.safe_load(f) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config must be a mapping: {candidate}")
            data = _deep_merge(data, loaded)
            break

    host = env_cz("HOST")
    if host:
        data.setdefault("adapter", {})["host"] = host
    port = env_cz("PORT")
    if port:
        data.setdefault("adapter", {})["port"] = int(port)
    api_key = env_cz("API_KEY")
    if api_key is not None:
        stripped = api_key.strip()
        # "unused" is the Hermes provider placeholder, not adapter HTTP auth.
        if stripped and stripped.lower() != "unused":
            data.setdefault("adapter", {})["api_key"] = stripped
    model = env_cz("MODEL")
    if model:
        data.setdefault("inference", {})["model"] = model
    backend = env_cz("BACKEND")
    if backend:
        data.setdefault("inference", {})["backend"] = backend
    tool_timeout = env_cz("TOOL_TIMEOUT_S")
    if tool_timeout:
        data.setdefault("inference", {}).setdefault("cursor", {})["tool_timeout_s"] = float(
            tool_timeout
        )

    return CZConfig.model_validate(data or {})
