"""Tool-loop harness (no live Cursor calls)."""

from __future__ import annotations

import threading
import time

from hcx.core.sessions import SessionStore


def test_parallel_park_and_deliver():
    store = SessionStore()
    session = store.create()
    a = session.park("web_search", '{"q":"x"}', call_id="call_a")
    b = session.park("terminal", '{"command":"ls"}', call_id="call_b")

    results: dict[str, str] = {}

    def waiter(call_id: str) -> None:
        results[call_id] = session.wait_result(call_id, timeout=2.0)

    t1 = threading.Thread(target=waiter, args=("call_a",))
    t2 = threading.Thread(target=waiter, args=("call_b",))
    t1.start()
    t2.start()
    time.sleep(0.05)
    assert session.deliver_result("call_a", "A")
    assert session.deliver_result("call_b", "B")
    t1.join(timeout=2)
    t2.join(timeout=2)
    assert results["call_a"] == "A"
    assert results["call_b"] == "B"
    assert a.call_id == "call_a"
    assert b.call_id == "call_b"
