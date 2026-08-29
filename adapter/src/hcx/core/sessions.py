"""Tool-loop session state for Hermes ↔ Cursor tool passthrough."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PendingToolCall:
    call_id: str
    name: str
    arguments: str  # JSON string
    result: str | None = None
    event: threading.Event = field(default_factory=threading.Event)


@dataclass
class ToolLoopSession:
    """One Hermes chat-completions turn that may need multiple tool round-trips.

    Flow:
      1. Adapter starts a Cursor run with Hermes tool schemas as custom tools.
      2. When Cursor invokes a custom tool, we park and expose the call to Hermes.
      3. Hermes executes the tool and POSTs role=tool messages.
      4. We unblock the parked call with the result; Cursor continues.
    """

    session_id: str
    created_at: float = field(default_factory=time.time)
    pending: dict[str, PendingToolCall] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    closed: bool = False

    def park(self, name: str, arguments: str, call_id: str | None = None) -> PendingToolCall:
        call_id = call_id or f"call_{uuid.uuid4().hex[:24]}"
        pending = PendingToolCall(call_id=call_id, name=name, arguments=arguments)
        with self.lock:
            self.pending[call_id] = pending
        return pending

    def deliver_result(self, call_id: str, result: str) -> bool:
        with self.lock:
            pending = self.pending.get(call_id)
            if not pending:
                return False
            pending.result = result
            pending.event.set()
            return True

    def wait_result(self, call_id: str, timeout: float = 300.0) -> str:
        with self.lock:
            pending = self.pending.get(call_id)
        if pending is None:
            raise KeyError(f"unknown tool call: {call_id}")
        if not pending.event.wait(timeout=timeout):
            raise TimeoutError(f"tool result timeout for {call_id}")
        return pending.result or ""

    def close(self) -> None:
        self.closed = True
        with self.lock:
            for p in self.pending.values():
                if not p.event.is_set():
                    p.result = p.result or '{"error":"session closed"}'
                    p.event.set()


class SessionStore:
    def __init__(self, ttl_seconds: float = 1800.0) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, ToolLoopSession] = {}
        self._lock = threading.Lock()

    def create(self) -> ToolLoopSession:
        sid = f"hcx_{uuid.uuid4().hex}"
        session = ToolLoopSession(session_id=sid)
        with self._lock:
            self._sessions[sid] = session
            self._purge_locked()
        return session

    def get(self, session_id: str) -> ToolLoopSession | None:
        with self._lock:
            self._purge_locked()
            return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> ToolLoopSession:
        if session_id:
            existing = self.get(session_id)
            if existing and not existing.closed:
                return existing
        return self.create()

    def _purge_locked(self) -> None:
        now = time.time()
        dead = [
            sid
            for sid, s in self._sessions.items()
            if s.closed or (now - s.created_at) > self._ttl
        ]
        for sid in dead:
            self._sessions.pop(sid, None)
