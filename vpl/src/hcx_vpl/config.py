"""Environment-driven VPL configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class VplConfig:
    enabled: bool = True
    layer_threshold_items: int = 5
    max_buckets: int = 4
    passthrough_max_words: int = 400
    session_ttl_sec: int = 1800
    label_max_words: int = 8

    @classmethod
    def from_env(cls) -> VplConfig:
        return cls(
            enabled=_env_bool("HCX_VPL_ENABLED", True),
            layer_threshold_items=_env_int("HCX_VPL_LAYER_THRESHOLD_ITEMS", 5),
            max_buckets=_env_int("HCX_VPL_MAX_BUCKETS", 4),
            passthrough_max_words=_env_int("HCX_VPL_PASSTHROUGH_MAX_WORDS", 400),
            session_ttl_sec=_env_int("HCX_VPL_SESSION_TTL_SEC", 1800),
        )
