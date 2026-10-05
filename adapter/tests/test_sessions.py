"""SessionStore and ToolLoopSession coverage."""

from __future__ import annotations

import time

import pytest
from construct_zero.core.sessions import SessionStore, ToolLoopSession


def test_session_store_get_or_create_and_purge():
    store = SessionStore(ttl_seconds=0.05)
    s1 = store.create()
    assert store.get(s1.session_id) is s1
    s1.close()
    time.sleep(0.06)
    assert store.get(s1.session_id) is None
    again = store.get_or_create(s1.session_id)
    assert again.session_id != s1.session_id


def test_wait_result_unknown_and_timeout():
    session = ToolLoopSession(session_id="cz_test")
    with pytest.raises(KeyError):
        session.wait_result("missing", timeout=0.01)
    session.park("tool", "{}", call_id="call_t")
    with pytest.raises(TimeoutError):
        session.wait_result("call_t", timeout=0.05)


def test_close_unblocks_pending():
    session = ToolLoopSession(session_id="cz_close")
    session.park("tool", "{}", call_id="call_c")
    session.close()
    assert session.wait_result("call_c", timeout=1.0)


def test_deliver_unknown_returns_false():
    session = ToolLoopSession(session_id="cz_x")
    assert session.deliver_result("nope", "x") is False
