"""Load hermesxcursor.yaml + environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _repo_root() -> Path:
    # adapter/src/hcx/config.py -> repo root
    return Path(__file__).resolve().parents[3]


def default_config_paths() -> list[Path]:
    root = _repo_root()
    return [
        Path(os.environ["HCX_CONFIG"]).expanduser()
        if os.environ.get("HCX_CONFIG")
        else None,
        Path.home() / ".hermesxcursor" / "config.yaml",
        root / "config" / "hermesxcursor.yaml",
        root / "config" / "hermesxcursor.yaml.example",
    ]


class CursorDriverConfig(BaseModel):
    api_key_env: str = "CURSOR_API_KEY"
    mode: str = "ask"
    workspace_isolation: bool = True
    # When True, use ACP CLI path for tool-bearing requests if agent binary exists
    prefer_acp_for_tools: bool = True
    agent_bin: str = ""  # empty = auto-detect cursor-agent / agent


class ClaudeCodeDriverConfig(BaseModel):
    enabled: bool = False


class InferenceConfig(BaseModel):
    backend: str = "cursor"
    model: str = "auto"
    cursor: CursorDriverConfig = Field(default_factory=CursorDriverConfig)
    claude_code: ClaudeCodeDriverConfig = Field(default_factory=ClaudeCodeDriverConfig)


class AdapterConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765
    api_key: str = ""


class HCXConfig(BaseModel):
    adapter: AdapterConfig = Field(default_factory=AdapterConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)

    def cursor_api_key(self) -> str:
        env_name = self.inference.cursor.api_key_env or "CURSOR_API_KEY"
        return (os.environ.get(env_name) or "").strip()


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: Path | None = None) -> HCXConfig:
    data: dict[str, Any] = {}
    if path is not None:
        candidates = [path]
    else:
        candidates = [p for p in default_config_paths() if p is not None]

    for candidate in candidates:
        if candidate.is_file():
            with candidate.open() as f:
                loaded = yaml.safe_load(f) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config must be a mapping: {candidate}")
            data = _deep_merge(data, loaded)
            break

    # Env overrides
    if os.environ.get("HCX_HOST"):
        data.setdefault("adapter", {})["host"] = os.environ["HCX_HOST"]
    if os.environ.get("HCX_PORT"):
        data.setdefault("adapter", {})["port"] = int(os.environ["HCX_PORT"])
    if os.environ.get("HCX_API_KEY") is not None:
        data.setdefault("adapter", {})["api_key"] = os.environ.get("HCX_API_KEY", "")
    if os.environ.get("HCX_MODEL"):
        data.setdefault("inference", {})["model"] = os.environ["HCX_MODEL"]
    if os.environ.get("HCX_BACKEND"):
        data.setdefault("inference", {})["backend"] = os.environ["HCX_BACKEND"]

    return HCXConfig.model_validate(data or {})
