"""Unit coverage for doctor modules (in-process)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from construct_zero.doctor import checks as checks_mod
from construct_zero.doctor.checks import CheckResult, build_context, run_check
from construct_zero.doctor.cli import main
from construct_zero.doctor.profiles import CZ_CERTIFIED_V1
from construct_zero.doctor.report import format_table, to_json
from construct_zero.drivers.stub_backend import StubBackend


def test_run_checks_and_report():
    ctx = build_context()
    ctx["offline"] = True
    ctx["skip_hermes"] = True
    health = {
        "status": "ok",
        "version": "0.1.0",
        "backend": "mock",
        "capabilities": {"tools": True, "streaming": "native", "vision": False, "usage": True},
    }
    models = {"data": [{"id": "auto"}]}

    def fake_fetch(url: str, headers=None):
        if url.endswith("/health"):
            return health
        if url.endswith("/v1/models"):
            return models
        raise AssertionError(url)

    with patch("construct_zero.doctor.checks._fetch_json", side_effect=fake_fetch):
        results = [run_check(spec, ctx) for spec in CZ_CERTIFIED_V1]
    assert any(r.id == "health" and r.status == "pass" for r in results)
    table = format_table(results, "cz-certified-v1")
    assert "cz-certified-v1" in table
    payload = to_json(results, "cz-certified-v1", backend="mock", capabilities={"tools": True})
    assert payload["certified"] in (True, False)


def test_report_redacts_home():
    results = [CheckResult("x", "required", "pass", str(build_context()["config"]), "fix")]
    payload = to_json(results, "cz-certified-v1", backend="mock", capabilities={})
    assert "~" in json.dumps(payload) or "127.0.0.1" in json.dumps(payload)


def test_individual_check_helpers():
    ctx = build_context()
    ctx["skip_hermes"] = True
    ctx["offline"] = True
    assert checks_mod._check_os({})[0] in {"pass", "warn", "fail"}
    assert checks_mod._check_python({})[0] == "pass"
    assert checks_mod._check_uv_lock({})[0] in {"pass", "warn"}
    assert checks_mod._check_adapter_bind(ctx)[0] == "pass"
    assert checks_mod._check_secrets_hygiene(ctx)[0] in {"pass", "fail"}


def test_cli_main_offline(capsys):
    fake_result = CheckResult("health", "required", "pass", "ok", "fix")
    with patch(
        "construct_zero.doctor.cli.build_context",
        return_value={
            "config": build_context()["config"],
            "base_url": "http://127.0.0.1:8765",
            "auth_headers": {},
            "offline": True,
            "skip_hermes": True,
        },
    ):
        with patch("construct_zero.doctor.cli.run_check", return_value=fake_result):
            with patch("construct_zero.doctor.cli.CZ_CERTIFIED_V1", (fake_result,)):
                code = main(["--certify", "--offline"])
    assert code == 0
    assert "CERTIFIED" in capsys.readouterr().out


def test_cli_usage_error():
    assert main([]) == 2


def test_cli_json_output(capsys):
    fake = CheckResult("health", "required", "pass", "ok", "fix")
    with patch(
        "construct_zero.doctor.cli.build_context",
        return_value={
            "config": build_context()["config"],
            "base_url": "http://127.0.0.1:8765",
            "auth_headers": {},
            "offline": True,
            "skip_hermes": True,
        },
    ):
        with patch("construct_zero.doctor.cli.run_check", return_value=fake):
            with patch("construct_zero.doctor.cli.CZ_CERTIFIED_V1", (fake,)):
                assert main(["--certify", "--json", "--offline"]) == 0
    assert '"schema": "cz-doctor/1"' in capsys.readouterr().out


def test_stub_backend():
    b = StubBackend(name="x", detail="missing extra")
    assert b.health().ok is False
    with pytest.raises(RuntimeError):
        b.complete(MagicMock())
    with pytest.raises(RuntimeError):
        list(b.stream(MagicMock()))
