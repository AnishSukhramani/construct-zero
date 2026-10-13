"""Resolve agent identity for adapter traffic."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path

from construct_zero.home.paths import cz_state_dir
from construct_zero.openai_types import ChatCompletionRequest


def _agent_keys_path() -> Path:
    return cz_state_dir() / "home" / "agent-keys.json"


def _load_agent_keys() -> dict[str, str]:
    path = _agent_keys_path()
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in (data.get("hashes") or {}).items()}


def issue_agent_key(agent_id: str) -> str:
    token = secrets.token_urlsafe(24)
    digest = hashlib.sha256(token.encode()).hexdigest()
    path = _agent_keys_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"hashes": _load_agent_keys()}
    data["hashes"][agent_id] = digest
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return token


def verify_agent_key(agent_id: str, token: str) -> bool:
    if not token:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    stored = _load_agent_keys().get(agent_id)
    if not stored:
        return False
    return hmac.compare_digest(digest, stored)


def resolve_agent(
    request_headers: dict[str, str],
    body: ChatCompletionRequest,
    authorization: str | None,
) -> tuple[str, str | None]:
    agent = (request_headers.get("x-cz-agent") or request_headers.get("X-CZ-Agent") or "").strip()
    if agent:
        session = request_headers.get("x-cz-session") or request_headers.get("X-CZ-Session")
        return agent, session

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        for aid in _load_agent_keys():
            if verify_agent_key(aid, token):
                return aid, None

    if body.user:
        return str(body.user), None

    ua = (request_headers.get("user-agent") or "").lower()
    for hint, aid in (
        ("hermes", "hermes"),
        ("cline", "cline"),
        ("aider", "aider"),
        ("openhands", "openhands"),
    ):
        if hint in ua:
            return aid, None

    return "unknown", None


def session_id_from_request(
    agent: str, body: ChatCompletionRequest, header_session: str | None
) -> str | None:
    if header_session:
        return header_session
    if not body.messages:
        return None
    first = body.messages[0].model_dump()
    blob = json.dumps(first, sort_keys=True)
    h = hashlib.sha256(f"{agent}:{blob}".encode()).hexdigest()[:16]
    return f"s_{h}"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
