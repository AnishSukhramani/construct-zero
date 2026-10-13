"""Identity resolution and checkpoint importers."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from construct_zero.home.identity import (
    estimate_tokens,
    issue_agent_key,
    resolve_agent,
    session_id_from_request,
    verify_agent_key,
)
from construct_zero.home.importers.base import import_checkpoint
from construct_zero.home.importers.claude import from_transcript
from construct_zero.home.importers.cursor import from_project
from construct_zero.home.importers.hermes import from_session
from construct_zero.openai_types import ChatCompletionRequest, ChatMessage


def test_agent_key_issue_verify(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CZ_STATE_DIR", str(tmp_path))
    token = issue_agent_key("hermes")
    assert verify_agent_key("hermes", token)
    assert not verify_agent_key("hermes", "wrong")


def test_resolve_agent_paths() -> None:
    body = ChatCompletionRequest(model="auto", messages=[ChatMessage(role="user", content="hi")])
    agent, sess = resolve_agent({"x-cz-agent": "cline", "x-cz-session": "s1"}, body, None)
    assert agent == "cline"
    assert sess == "s1"
    agent2, _ = resolve_agent({}, body, None)
    assert agent2 == "unknown"
    body2 = ChatCompletionRequest(
        model="auto",
        messages=[ChatMessage(role="user", content="hi")],
        user="my-user",
    )
    agent3, _ = resolve_agent({}, body2, None)
    assert agent3 == "my-user"
    agent4, _ = resolve_agent({"user-agent": "Hermes/1.0"}, body, None)
    assert agent4 == "hermes"


def test_session_id_and_tokens() -> None:
    body = ChatCompletionRequest(
        model="auto",
        messages=[ChatMessage(role="user", content="hello")],
    )
    sid = session_id_from_request("agent", body, None)
    assert sid and sid.startswith("s_")
    assert estimate_tokens("abcd") >= 1


def test_claude_importer(tmp_path: Path, monkeypatch) -> None:
    enc = base64.urlsafe_b64encode(str(tmp_path.resolve()).encode()).decode().rstrip("=")
    base = Path.home() / ".claude" / "projects" / enc
    base.mkdir(parents=True, exist_ok=True)
    log = base / "sess.jsonl"
    rows = [
        {"role": "user", "content": "Build feature X"},
        {"role": "assistant", "content": "Working on todos"},
        {"is_error": True, "content": "rate limit"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    cp = from_transcript(tmp_path)
    assert "feature" in cp.goal.lower() or cp.goal
    assert cp.last_error


def test_cursor_and_hermes_importers(tmp_path: Path) -> None:
    subprocess = __import__("subprocess")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    cp = from_project(tmp_path)
    assert cp.from_agent == "cursor"
    cp2 = from_session(tmp_path)
    assert cp2.from_agent == "hermes"
    cp3 = import_checkpoint(tmp_path, "cursor", reason="manual")
    assert cp3.reason == "manual"
