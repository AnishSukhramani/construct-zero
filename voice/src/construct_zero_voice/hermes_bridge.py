"""Invoke project Hermes CLI for a one-shot chat turn."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

import httpx

from construct_zero_voice.envcompat import env_cz

logger = logging.getLogger(__name__)


def repo_root() -> Path:
    env = (env_cz("REPO_ROOT") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "scripts" / "start-voice.sh").is_file() and (p / "voice").is_dir():
            return p
    # Editable src layout: voice/src/construct_zero_voice/…
    return here.parents[3]


def default_hermes_bin() -> Path:
    env = (env_cz("HERMES_BIN") or "").strip()
    if env:
        return Path(env)
    root = repo_root()
    candidate = root / ".venvs" / "hermes" / "bin" / "hermes"
    if candidate.is_file():
        return candidate
    return Path("hermes")


def adapter_health_url() -> str:
    return (env_cz("HEALTH_URL") or "http://127.0.0.1:8765/health").strip()


def check_adapter_up(timeout: float = 2.0) -> tuple[bool, str]:
    url = adapter_health_url()
    try:
        r = httpx.get(url, timeout=timeout)
        if r.status_code != 200:
            return False, f"adapter health HTTP {r.status_code}"
        data = r.json()
        if data.get("status") != "ok":
            return False, data.get("detail") or "adapter not ok"
        return True, "ok"
    except Exception as exc:
        return False, f"adapter unreachable: {exc}"


# Compat alias for one release
check_hcx_up = check_adapter_up
hcx_health_url = adapter_health_url


_BOX_RE = re.compile(
    r"╭─.*?Hermes.*?╮\s*\n(?P<body>.*?)\n╰─+",
    re.DOTALL | re.IGNORECASE,
)


def parse_hermes_reply(stdout: str) -> str:
    """Extract assistant text from Hermes CLI output."""
    text = stdout or ""
    m = _BOX_RE.search(text)
    if m:
        body = m.group("body")
        lines = []
        for line in body.splitlines():
            line = re.sub(r"\x1b\[[0-9;]*m", "", line)
            line = line.strip()
            if line.startswith("│") or line.startswith("|"):
                line = line[1:]
            if line.endswith("│") or line.endswith("|"):
                line = line[:-1]
            line = line.strip()
            if line:
                lines.append(line)
        body = "\n".join(lines).strip()
        if body:
            return body

    # Fallback: last non-empty block after "Initializing agent"
    cleaned = re.sub(r"\x1b\[[0-9;]*m", "", text)
    parts = cleaned.split("Initializing agent")
    chunk = parts[-1] if parts else cleaned
    # Drop known footers
    for marker in ("Resume this session", "Session:", "Goodbye"):
        if marker in chunk:
            chunk = chunk.split(marker)[0]
    lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
    # Filter UI chrome
    skip_prefixes = ("──", "╭", "╰", "│", "⚠", "●", "Query:", "Duration:", "Messages:")
    kept = [
        ln
        for ln in lines
        if not any(ln.startswith(p) for p in skip_prefixes)
        and "Hermes Agent" not in ln
    ]
    return "\n".join(kept).strip() or cleaned.strip()


def ask_hermes(
    prompt: str,
    *,
    provider: str = "construct-zero",
    model: str = "auto",
    timeout: float | None = None,
) -> str:
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("empty prompt")

    ok, detail = check_adapter_up()
    if not ok:
        raise RuntimeError(detail)

    hermes_bin = default_hermes_bin()
    timeout = timeout or float(env_cz("VOICE_HERMES_TIMEOUT") or "180")
    cmd = [
        str(hermes_bin),
        "chat",
        "-q",
        prompt,
        "--provider",
        provider,
        "--model",
        model,
    ]
    env = os.environ.copy()
    env.setdefault("CZ_API_KEY", "unused")
    env.setdefault("HCX_API_KEY", env.get("CZ_API_KEY", "unused"))

    logger.info("Running Hermes: %s", " ".join(cmd[:4]) + " …")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(repo_root()),
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"hermes binary not found ({hermes_bin}). "
            "Install with: uv venv .venvs/hermes && uv pip install -e './hermes[all]'"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Hermes timed out after {timeout}s") from exc

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        logger.error("Hermes exit %s: %s", proc.returncode, out[-2000:])
        raise RuntimeError(f"Hermes failed (exit {proc.returncode}): {out[-500:]}")

    reply = parse_hermes_reply(proc.stdout or "")
    if not reply:
        raise RuntimeError("Hermes returned empty reply")
    return reply
