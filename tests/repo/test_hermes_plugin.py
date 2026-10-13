"""Hermes construct-zero provider stub (no upstream Hermes install)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_INIT = ROOT / "hermes-plugin" / "model-providers" / "construct-zero" / "__init__.py"


def _load_plugin():
    providers = types.ModuleType("providers")
    base = types.ModuleType("providers.base")
    registered: list[object] = []

    class ProviderProfile:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def register_provider(profile: object) -> None:
        registered.append(profile)

    base.ProviderProfile = ProviderProfile
    providers.base = base
    providers.register_provider = register_provider
    sys.modules["providers"] = providers
    sys.modules["providers.base"] = base

    spec = importlib.util.spec_from_file_location("cz_hermes_plugin", PLUGIN_INIT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return registered, mod


def test_hermes_plugin_registers_construct_zero():
    registered, mod = _load_plugin()
    assert len(registered) == 1
    profile = registered[0]
    assert profile.name == "construct-zero"
    assert "cz" in profile.aliases
    assert profile.base_url == "http://127.0.0.1:8765/v1"
    assert hasattr(mod, "construct_zero")
