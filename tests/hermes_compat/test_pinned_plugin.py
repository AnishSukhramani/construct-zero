"""Hermes Watch assertions at the pinned ref (HERMES_PIN_ROOT + HERMES_HOME plugin)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = ROOT / "hermes-plugin" / "model-providers" / "construct-zero"
SNIPPET = ROOT / "config" / "hermes.config.snippet.yaml"


def test_hermes_source_present(hermes_pin_root: Path) -> None:
    assert (hermes_pin_root / "pyproject.toml").is_file() or (
        hermes_pin_root / "setup.py"
    ).is_file()


def test_construct_zero_plugin_yaml_manifest(hermes_pin_root: Path) -> None:
    plugin_yaml = PLUGIN_DIR / "plugin.yaml"
    assert plugin_yaml.is_file()
    data = yaml.safe_load(plugin_yaml.read_text())
    assert data.get("kind") == "model-provider"
    assert "construct-zero" in json.dumps(data)


def test_plugins_compat_user_plugin_import(hermes_pin_env: Path) -> None:
    import providers  # noqa: F401 — pinned Hermes checkout on sys.path

    profile = providers.get_provider_profile("construct-zero")
    assert profile is not None


def test_provider_profile_kwargs_and_aliases(hermes_pin_env: Path) -> None:
    import providers

    profile = providers.get_provider_profile("cz")
    assert profile is not None
    assert profile.name == "construct-zero"
    assert profile.api_mode == "chat_completions"
    assert profile.auth_type == "api_key"
    assert profile.base_url.rstrip("/") == "http://127.0.0.1:8765/v1"
    assert "hcx" in profile.aliases


def test_compression_cap_256k_default(hermes_pin_env: Path) -> None:
    from agent.model_metadata import CONTEXT_PROBE_TIERS, DEFAULT_FALLBACK_CONTEXT

    assert CONTEXT_PROBE_TIERS[0] == 256_000
    assert DEFAULT_FALLBACK_CONTEXT == 256_000


def test_context_length_pin_in_snippet() -> None:
    data = yaml.safe_load(SNIPPET.read_text())
    assert data["model"]["context_length"] == 256_000


def test_hermes_home_scratch_plugin_path(hermes_pin_env: Path) -> None:
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    plugin_root = home / "plugins" / "model-providers" / "construct-zero"
    assert plugin_root.is_symlink() or plugin_root.is_dir()
    assert (plugin_root / "plugin.yaml").is_file()
