"""In-memory VPL session store with TTL."""

from __future__ import annotations

import time

from hcx_vpl.models import SessionState


class SessionStore:
    def __init__(self, ttl_sec: int = 1800) -> None:
        self._ttl = ttl_sec
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str | None) -> SessionState | None:
        if not session_id:
            return None
        self._purge_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._is_expired(session):
            self._sessions.pop(session_id, None)
            return None
        return session

    def put(self, session: SessionState) -> None:
        self._purge_expired()
        self._sessions[session.session_id] = session

    def delete(self, session_id: str | None) -> None:
        if session_id:
            self._sessions.pop(session_id, None)

    def clear(self) -> None:
        self._sessions.clear()

    def _is_expired(self, session: SessionState) -> bool:
        if session.created_at <= 0:
            return False
        return (time.time() - session.created_at) > self._ttl

    def _purge_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if self._is_expired(s)]
        for sid in expired:
            self._sessions.pop(sid, None)
