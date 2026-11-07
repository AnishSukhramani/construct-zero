"""Individual doctor --certify checks."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from construct_zero import __version__
from construct_zero.config import load_config
from construct_zero.doctor.profiles import CheckSpec
from construct_zero.security.project_root import (
    agent_context_is_cz_source,
    cz_install_root,
    is_nested_cz_install,
    resolve_user_project_root,
)
from construct_zero.security.redact import redact


@dataclass
class CheckResult:
    id: str
    severity: str
    status: str  # pass | fail | skip | warn
    detail: str
    fix: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _redact_path(p: str) -> str:
    home = str(Path.home())
    if p.startswith(home):
        return "~" + p[len(home) :]
    return redact(p)


def run_check(spec: CheckSpec, ctx: dict[str, Any]) -> CheckResult:
    fn = CHECKS.get(spec.id)
    if fn is None:
        return CheckResult(spec.id, spec.severity, "skip", "not implemented", spec.fix)
    status, detail = fn(ctx)
    return CheckResult(spec.id, spec.severity, status, redact(detail), spec.fix)


def _check_os(_ctx: dict[str, Any]) -> tuple[str, str]:
    sysname = platform.system()
    if sysname == "Linux" and "microsoft" in platform.release().lower():
        return "warn", "WSL detected (advisory)"
    if sysname in {"Darwin", "Linux"}:
        return "pass", f"{sysname} {platform.release()} {platform.machine()}"
    return "fail", f"Unsupported OS: {sysname}"


def _check_wsl(_ctx: dict[str, Any]) -> tuple[str, str]:
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        return "warn", "Running under WSL2 — see docs/recipes/wsl.md"
    return "pass", "not WSL"


def _check_python(_ctx: dict[str, Any]) -> tuple[str, str]:
    v = sys.version_info
    if (v.major, v.minor) < (3, 10) or (v.major, v.minor) > (3, 12):
        return "fail", f"Python {v.major}.{v.minor} outside supported 3.10–3.12"
    return "pass", f"{v.major}.{v.minor}.{v.micro}"


def _check_uv_lock(_ctx: dict[str, Any]) -> tuple[str, str]:
    lock = _repo_root() / "adapter" / "uv.lock"
    if not lock.is_file():
        return "warn", "adapter/uv.lock missing"
    return "pass", "uv.lock present"


def _check_adapter_bind(ctx: dict[str, Any]) -> tuple[str, str]:
    cfg = ctx["config"]
    host = cfg.adapter.host
    if host not in {"127.0.0.1", "localhost"}:
        return "fail", f"adapter.host={host!r} (must be loopback)"
    port = int(cfg.adapter.port)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
    except OSError:
        pass  # port in use is ok — adapter may be running
    return "pass", f"{host}:{port}"


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def _check_health(ctx: dict[str, Any]) -> tuple[str, str]:
    base = ctx["base_url"]
    try:
        data = _fetch_json(f"{base}/health")
    except Exception as exc:
        return "fail", f"/health unreachable: {exc}"
    if data.get("status") != "ok":
        return "fail", data.get("detail") or "status not ok"
    if data.get("version") != __version__:
        return "warn", f"version {data.get('version')} != package {__version__}"
    return "pass", "ok"


def _check_backend(ctx: dict[str, Any]) -> tuple[str, str]:
    base = ctx["base_url"]
    try:
        data = _fetch_json(f"{base}/health")
    except Exception as exc:
        return "fail", str(exc)
    caps = data.get("capabilities") or {}
    backend = data.get("backend", "")
    if backend == "cursor":
        cfg = ctx["config"]
        if cfg.inference.cursor.mode != "ask":
            return "fail", f"cursor.mode={cfg.inference.cursor.mode!r}"
    streaming = caps.get("streaming", "?")
    return "pass", f"backend={backend} streaming={streaming}"


def _check_models(ctx: dict[str, Any]) -> tuple[str, str]:
    base = ctx["base_url"]
    try:
        data = _fetch_json(f"{base}/v1/models", ctx.get("auth_headers"))
    except Exception as exc:
        return "fail", str(exc)
    ids = [x.get("id") for x in data.get("data", []) if isinstance(x, dict)]
    if not ids:
        return "fail", "empty model list"
    return "pass", f"{len(ids)} model(s)"


def _check_chat(ctx: dict[str, Any]) -> tuple[str, str]:
    if ctx.get("offline"):
        return "skip", "offline mode"
    base = ctx["base_url"]
    body = json.dumps(
        {"model": "auto", "messages": [{"role": "user", "content": "Reply PONG"}]}
    ).encode()
    headers = {"Content-Type": "application/json", **(ctx.get("auth_headers") or {})}
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        return "fail", str(exc)
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    if "PONG" not in text.upper() and "mock:" not in text:
        return "fail", f"unexpected reply: {text[:80]!r}"
    return "pass", "PONG ok"


def _check_tools(ctx: dict[str, Any]) -> tuple[str, str]:
    if ctx.get("offline"):
        return "skip", "offline mode"
    base = ctx["base_url"]
    body = json.dumps(
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "tool test"}],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": "noop", "parameters": {"type": "object"}},
                }
            ],
        }
    ).encode()
    headers = {"Content-Type": "application/json", **(ctx.get("auth_headers") or {})}
    req = urllib.request.Request(f"{base}/v1/chat/completions", data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.status
            json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 501:
            return "skip", "backend has no tools"
        return "fail", f"HTTP {exc.code}"
    except Exception as exc:
        return "fail", str(exc)
    if code >= 500:
        return "fail", f"HTTP {code}"
    return "pass", f"HTTP {code}"


def _check_hermes_pin(ctx: dict[str, Any]) -> tuple[str, str]:
    if ctx.get("skip_hermes"):
        return "skip", "CZ_DOCTOR_SKIP_HERMES"
    root = _repo_root()
    hermes = root / "hermes"
    lock = root / "config" / "upstream.lock.yaml"
    if not hermes.exists():
        return "fail", "hermes/ missing"
    if not lock.is_file():
        return "fail", "upstream.lock.yaml missing"
    ref = ""
    for line in lock.read_text().splitlines():
        if line.strip().startswith("ref:"):
            ref = line.split(":", 1)[1].strip().strip("'\"")
            break
    if not ref:
        return "fail", "no ref in lock file"
    try:
        head = subprocess.check_output(
            ["git", "-C", str(hermes), "rev-parse", "HEAD"], text=True
        ).strip()
        pinned = subprocess.check_output(
            ["git", "-C", str(hermes), "rev-parse", ref], text=True
        ).strip()
    except subprocess.CalledProcessError as exc:
        return "fail", str(exc)
    if head != pinned:
        return "fail", f"HEAD {head[:8]} != pin {pinned[:8]}"
    return "pass", head[:12]


def _check_hermes_plugin(ctx: dict[str, Any]) -> tuple[str, str]:
    if ctx.get("skip_hermes"):
        return "skip", "CZ_DOCTOR_SKIP_HERMES"
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    plugin = home / "plugins" / "construct-zero"
    if not plugin.exists():
        return "fail", f"missing {_redact_path(str(plugin))}"
    return "pass", "plugin present"


def _check_hermes_config(ctx: dict[str, Any]) -> tuple[str, str]:
    if ctx.get("skip_hermes"):
        return "skip", "CZ_DOCTOR_SKIP_HERMES"
    cfg_path = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "config.yaml"
    if not cfg_path.is_file():
        return "fail", f"missing {_redact_path(str(cfg_path))}"
    text = cfg_path.read_text()
    if "construct-zero" not in text:
        return "fail", "provider construct-zero not set"
    port = ctx["config"].adapter.port
    if f"127.0.0.1:{port}/v1" not in text and f"localhost:{port}/v1" not in text:
        return "fail", f"base_url should include port {port}"
    return "pass", "provider + base_url ok"


def _check_client_cline(_ctx: dict[str, Any]) -> tuple[str, str]:
    return "warn", "run ./construct-zero doctor --client=cline locally"


def _check_errors(_ctx: dict[str, Any]) -> tuple[str, str]:
    snap = _repo_root() / "tests" / "first_run" / "snapshots"
    if not snap.is_dir():
        return "warn", "snapshots dir missing"
    return "pass", f"{len(list(snap.glob('*.txt')))} snapshot(s)"


def _check_project_isolation(_ctx: dict[str, Any]) -> tuple[str, str]:
    install = cz_install_root()
    project = resolve_user_project_root()
    if agent_context_is_cz_source(project):
        return (
            "fail",
            f"agent project root is the CZ install ({_redact_path(str(install))}); "
            "set CZ_PROJECT_ROOT to your app repo or install CZ as .cz/ or ../construct-zero",
        )
    if is_nested_cz_install(install) and project == install:
        return (
            "warn",
            f"nested install but project root is still {_redact_path(str(install))}; "
            "export CZ_PROJECT_ROOT or run Hermes from the parent repo",
        )
    if project != install:
        return "pass", f"project={_redact_path(str(project))} install={_redact_path(str(install))}"
    return "pass", f"standalone install at {_redact_path(str(install))}"


def _check_adapter_auth(ctx: dict[str, Any]) -> tuple[str, str]:
    key = (ctx["config"].adapter.api_key or "").strip()
    if not key or key.lower() == "unused":
        return (
            "warn",
            "adapter.api_key unset — loopback open to local processes; "
            "set a bearer key for defense in depth",
        )
    return "pass", "adapter bearer configured"


def _check_secrets_hygiene(ctx: dict[str, Any]) -> tuple[str, str]:
    root = _repo_root()
    env_path = root / ".env"
    if env_path.is_file():
        mode = env_path.stat().st_mode & 0o777
        if mode & 0o044:
            return "fail", f".env mode {oct(mode)} too open (want 600)"
    for p in (root / "config").glob("*.yaml"):
        if p.name.endswith(".example"):
            continue
        text = p.read_text(errors="ignore")
        if "CURSOR_API_KEY" in text or "sk-" in text:
            return "fail", f"possible secret in {_redact_path(str(p))}"
    return "pass", "ok"


CHECKS = {
    "os": _check_os,
    "wsl": _check_wsl,
    "python": _check_python,
    "uv-lock": _check_uv_lock,
    "adapter-bind": _check_adapter_bind,
    "health": _check_health,
    "backend": _check_backend,
    "models": _check_models,
    "chat": _check_chat,
    "tools": _check_tools,
    "hermes-pin": _check_hermes_pin,
    "hermes-plugin": _check_hermes_plugin,
    "hermes-config": _check_hermes_config,
    "client:cline": _check_client_cline,
    "errors": _check_errors,
    "secrets-hygiene": _check_secrets_hygiene,
    "project-isolation": _check_project_isolation,
    "adapter-auth": _check_adapter_auth,
}


def build_context() -> dict[str, Any]:
    cfg = load_config()
    host = cfg.adapter.host
    port = cfg.adapter.port
    base = f"http://{host}:{port}"
    headers: dict[str, str] = {}
    key = (cfg.adapter.api_key or "").strip()
    if key and key.lower() != "unused":
        headers["Authorization"] = f"Bearer {key}"
    return {
        "config": cfg,
        "base_url": base,
        "auth_headers": headers,
        "offline": os.environ.get("CZ_DOCTOR_CERTIFY_OFFLINE", "0") == "1",
        "skip_hermes": os.environ.get("CZ_DOCTOR_SKIP_HERMES", "0") == "1",
    }
