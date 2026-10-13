"""Additional config loading paths."""

from __future__ import annotations

import pytest
from construct_zero.config import CZConfig, default_config_paths, load_config


def test_cursor_api_key_from_env(monkeypatch):
    cfg = CZConfig()
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    assert cfg.cursor_api_key() == ""
    monkeypatch.setenv("CURSOR_API_KEY", "  key123  ")
    assert cfg.cursor_api_key() == "key123"


def test_load_config_invalid_yaml_mapping(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not\n- a\n- mapping\n")
    with pytest.raises(ValueError, match="mapping"):
        load_config(bad)


def test_env_overrides_port_and_backend(monkeypatch, tmp_path):
    cfg_path = tmp_path / "cz.yaml"
    cfg_path.write_text("adapter:\n  port: 8765\n")
    monkeypatch.setenv("CZ_PORT", "9999")
    monkeypatch.setenv("CZ_BACKEND", "cursor")
    monkeypatch.setenv("CZ_MODEL", "composer-2.5")
    cfg = load_config(cfg_path)
    assert cfg.adapter.port == 9999
    assert cfg.inference.backend == "cursor"
    assert cfg.inference.model == "composer-2.5"


def test_default_config_paths_includes_example():
    paths = default_config_paths()
    assert any(p.name.endswith(".example") for p in paths)
