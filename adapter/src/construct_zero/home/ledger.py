"""Usage ledger (SQLite WAL) — no prompt/completion content."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from construct_zero.home.paths import cz_state_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  agent TEXT NOT NULL,
  session TEXT,
  project TEXT,
  backend TEXT,
  model TEXT,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  estimated INTEGER NOT NULL DEFAULT 1,
  cost_usd REAL,
  source TEXT NOT NULL,
  request_id TEXT,
  status INTEGER
);
CREATE INDEX IF NOT EXISTS usage_ts ON usage(ts);
CREATE INDEX IF NOT EXISTS usage_agent ON usage(agent, ts);
"""

CONTENT_COLUMNS = frozenset({"prompt", "completion", "content", "messages", "body"})


def usage_db_path() -> Path:
    return cz_state_dir() / "usage.db"


def init_db(path: Path | None = None) -> None:
    db = path or usage_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def assert_schema_no_content_columns(path: Path | None = None) -> None:
    db = path or usage_db_path()
    init_db(db)
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("PRAGMA table_info(usage)").fetchall()
        names = {r[1].lower() for r in rows}
        bad = names & CONTENT_COLUMNS
        if bad:
            raise AssertionError(f"forbidden content columns: {bad}")
    finally:
        conn.close()


def record_usage(
    *,
    agent: str,
    session: str | None = None,
    project: str | None = None,
    backend: str = "adapter",
    model: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated: bool = True,
    cost_usd: float | None = None,
    source: str = "adapter",
    request_id: str | None = None,
    status: int = 200,
    db_path: Path | None = None,
) -> None:
    init_db(db_path)
    total = prompt_tokens + completion_tokens
    conn = sqlite3.connect(db_path or usage_db_path())
    try:
        conn.execute(
            """
            INSERT INTO usage(
              ts, agent, session, project, backend, model,
              prompt_tokens, completion_tokens, total_tokens,
              estimated, cost_usd, source, request_id, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                agent,
                session,
                project,
                backend,
                model,
                prompt_tokens,
                completion_tokens,
                total,
                1 if estimated else 0,
                cost_usd,
                source,
                request_id,
                status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def aggregate_usage(
    *,
    since: str | None = None,
    until: str | None = None,
    group_by: str = "agent",
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path or usage_db_path())
    try:
        where = "1=1"
        params: list[Any] = []
        if since:
            where += " AND ts >= ?"
            params.append(since)
        if until:
            where += " AND ts <= ?"
            params.append(until)
        if group_by == "day":
            key = "substr(ts,1,10)"
        elif group_by == "model":
            key = "model"
        else:
            key = "agent"
        sql = f"""
            SELECT {key} AS k,
                   SUM(total_tokens) AS tokens,
                   SUM(CASE WHEN estimated=1 THEN total_tokens ELSE 0 END) AS estimated_tokens,
                   COUNT(*) AS requests
            FROM usage WHERE {where}
            GROUP BY k ORDER BY tokens DESC
        """
        rows = conn.execute(sql, params).fetchall()
        return [
            {
                "key": r[0],
                "total_tokens": r[1] or 0,
                "estimated_tokens": r[2] or 0,
                "requests": r[3] or 0,
            }
            for r in rows
        ]
    finally:
        conn.close()


def sum_tokens(
    *,
    agent: str | None = None,
    session: str | None = None,
    since_ts: str | None = None,
    db_path: Path | None = None,
) -> int:
    init_db(db_path)
    conn = sqlite3.connect(db_path or usage_db_path())
    try:
        where = "1=1"
        params: list[Any] = []
        if agent:
            where += " AND agent = ?"
            params.append(agent)
        if session:
            where += " AND session = ?"
            params.append(session)
        if since_ts:
            where += " AND ts >= ?"
            params.append(since_ts)
        row = conn.execute(
            f"SELECT COALESCE(SUM(total_tokens),0) FROM usage WHERE {where}", params
        ).fetchone()
        return int(row[0] if row else 0)
    finally:
        conn.close()
