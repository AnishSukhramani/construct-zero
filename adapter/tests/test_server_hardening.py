"""Loopback Host / Origin hardening on the adapter."""

from __future__ import annotations

from construct_zero.config import CZConfig
from construct_zero.server import create_app
from fastapi.testclient import TestClient


def test_rejects_non_loopback_host_header() -> None:
    app = create_app(CZConfig())
    client = TestClient(app)
    resp = client.get("/health", headers={"Host": "evil.example.com"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "cz_forbidden_host"


def test_rejects_non_loopback_origin() -> None:
    app = create_app(CZConfig())
    client = TestClient(app)
    resp = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "cz_forbidden_origin"


def test_allows_localhost_host() -> None:
    app = create_app(CZConfig())
    client = TestClient(app, base_url="http://127.0.0.1")
    resp = client.get("/health", headers={"Host": "127.0.0.1:8765"})
    assert resp.status_code == 200
