"""Fixtures for contract tests."""

from __future__ import annotations

import pytest
from construct_zero.config import CZConfig, InferenceConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def mock_client() -> TestClient:
    cfg = CZConfig(inference=InferenceConfig(backend="mock"))
    return TestClient(create_app(cfg))


@pytest.fixture
def cursor_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CURSOR_API_KEY", "fake-key-for-tests")
    cfg = CZConfig(inference=InferenceConfig(backend="cursor"))
    return TestClient(create_app(cfg))
