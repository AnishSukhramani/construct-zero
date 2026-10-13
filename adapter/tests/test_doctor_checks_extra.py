"""Additional doctor check branches."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

from construct_zero.doctor import checks as checks_mod
from construct_zero.doctor.checks import build_context, run_check
from construct_zero.doctor.profiles import CheckSpec


def test_chat_and_tools_online():
    ctx = build_context()
    ctx["offline"] = False
    chat_body = json.dumps({"choices": [{"message": {"content": "PONG"}}]}).encode()
    tool_body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    class Resp:
        def __init__(self, body: bytes, status: int = 200):
            self._body = body
            self.status = status

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def urlopen(req, timeout=0):
        if b'"tools"' in req.data:
            return Resp(tool_body)
        return Resp(chat_body)

    with patch("urllib.request.urlopen", side_effect=urlopen):
        chat = run_check(CheckSpec("chat", "required", "", ""), ctx)
        tools = run_check(CheckSpec("tools", "required", "", ""), ctx)
    assert chat.status == "pass"
    assert tools.status == "pass"


def test_chat_http_error():
    ctx = build_context()
    ctx["offline"] = False

    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError("url", 502, "bad", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=urlopen):
        r = run_check(CheckSpec("chat", "required", "", ""), ctx)
    assert r.status == "fail"


def test_tools_fail_on_500():
    ctx = build_context()
    ctx["offline"] = False

    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError("url", 500, "err", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=urlopen):
        r = run_check(CheckSpec("tools", "required", "", ""), ctx)
    assert r.status == "fail"


def test_tools_501_skips():
    ctx = build_context()
    ctx["offline"] = False

    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError("url", 501, "no tools", hdrs=None, fp=None)

    with patch("urllib.request.urlopen", side_effect=urlopen):
        r = run_check(CheckSpec("tools", "required", "", ""), ctx)
    assert r.status == "skip"


def test_health_and_models_failures():
    ctx = build_context()

    def boom(url, headers=None):
        raise OSError("down")

    with patch("construct_zero.doctor.checks._fetch_json", side_effect=boom):
        h = run_check(CheckSpec("health", "required", "", ""), ctx)
        m = run_check(CheckSpec("models", "required", "", ""), ctx)
    assert h.status == "fail"
    assert m.status == "fail"


def test_backend_cursor_ask_mode():
    ctx = build_context()
    ctx["config"].inference.cursor.mode = "agent"
    with patch(
        "construct_zero.doctor.checks._fetch_json",
        return_value={"status": "ok", "backend": "cursor", "capabilities": {}},
    ):
        r = run_check(CheckSpec("backend", "required", "", ""), ctx)
    assert r.status == "fail"


def test_chat_fail_without_pong():
    ctx = build_context()
    ctx["offline"] = False
    body = json.dumps({"choices": [{"message": {"content": "nope"}}]}).encode()

    class Resp:
        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    with patch("urllib.request.urlopen", return_value=Resp()):
        r = run_check(CheckSpec("chat", "required", "", ""), ctx)
    assert r.status == "fail"


def test_secrets_hygiene_env_mode(tmp_path, monkeypatch):
    envf = tmp_path / ".env"
    envf.write_text("CURSOR_API_KEY=placeholder\n")
    envf.chmod(0o644)
    monkeypatch.setattr("construct_zero.doctor.checks._repo_root", lambda: tmp_path)
    ctx = build_context()
    r = run_check(CheckSpec("secrets-hygiene", "required", "", ""), ctx)
    assert r.status == "fail"


def test_hermes_config_wrong_provider(tmp_path, monkeypatch):
    home = tmp_path / "hermeshome"
    home.mkdir()
    (home / "config.yaml").write_text("model:\n  provider: openai\n")
    monkeypatch.setenv("HERMES_HOME", str(home))
    ctx = build_context()
    r = run_check(CheckSpec("hermes-config", "required", "", ""), ctx)
    assert r.status == "fail"


def test_hermes_plugin_missing(tmp_path, monkeypatch):
    home = tmp_path / "hermeshome"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    ctx = build_context()
    ctx["skip_hermes"] = False
    r = run_check(CheckSpec("hermes-plugin", "required", "", ""), ctx)
    assert r.status == "fail"


def test_models_empty_list():
    ctx = build_context()
    with patch("construct_zero.doctor.checks._fetch_json", return_value={"data": []}):
        r = run_check(CheckSpec("models", "required", "", ""), ctx)
    assert r.status == "fail"


def test_health_not_ok():
    ctx = build_context()
    with patch(
        "construct_zero.doctor.checks._fetch_json",
        return_value={"status": "error", "detail": "broken"},
    ):
        r = run_check(CheckSpec("health", "required", "", ""), ctx)
    assert r.status == "fail"


def test_health_version_mismatch_warn():
    ctx = build_context()
    with patch(
        "construct_zero.doctor.checks._fetch_json",
        return_value={"status": "ok", "version": "9.9.9", "backend": "mock"},
    ):
        r = run_check(CheckSpec("health", "required", "", ""), ctx)
    assert r.status == "warn"


def test_os_unsupported(monkeypatch):
    import platform as plat

    monkeypatch.setattr(plat, "system", lambda: "Windows")
    monkeypatch.setattr(plat, "release", lambda: "10")
    monkeypatch.setattr(plat, "machine", lambda: "AMD64")
    assert checks_mod._check_os({})[0] == "fail"


def test_advisory_checks():
    ctx = build_context()
    assert run_check(CheckSpec("client:cline", "advisory", "", ""), ctx).status == "warn"
    assert run_check(CheckSpec("errors", "advisory", "", ""), ctx).status == "pass"
    assert run_check(CheckSpec("wsl", "advisory", "", ""), ctx).status in {"pass", "warn"}


def test_hermes_checks_skip():
    ctx = build_context()
    ctx["skip_hermes"] = True
    for cid in ("hermes-pin", "hermes-plugin", "hermes-config"):
        r = run_check(CheckSpec(cid, "required", "", ""), ctx)
        assert r.status == "skip"
