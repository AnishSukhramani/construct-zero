"""Tests for `.cz/` store (PR 18)."""

from __future__ import annotations

import multiprocessing
import os
import subprocess
from pathlib import Path

from construct_zero.home.store import CzStore, _parse_memory_entries


def test_init_idempotent(tmp_path: Path) -> None:
    store = CzStore(tmp_path)
    first = store.init_scaffold()
    assert first
    second = store.init_scaffold()
    assert second == []
    assert (tmp_path / ".cz" / "CONTEXT.md").is_file()


def test_memory_add_list_supersede_expire(tmp_path: Path) -> None:
    store = CzStore(tmp_path)
    store.init_scaffold()
    eid = store.memory_add("First fact", "Body one")
    assert eid.startswith("M-")
    active = store.memory_list()
    assert len(active) == 1
    store.memory_expire(eid)
    assert store.memory_list() == []
    assert len(store.memory_list(include_all=True)) == 1
    eid2 = store.memory_add("Second", "Body two")
    new_id = store.memory_supersede(eid2, "Second v2", "Updated")
    assert new_id != eid2
    text = store.read_memory()
    assert "superseded" in text
    assert f"supersedes: {eid2}" in text


def test_conflict_file_on_hash_mismatch(tmp_path: Path) -> None:
    store = CzStore(tmp_path)
    store.init_scaffold()
    eid = store.memory_add("X", "content")
    entries = _parse_memory_entries(store.read_memory())
    h = entries[eid].content_hash
    # Simulate concurrent edit without updating hash expectation
    path = tmp_path / ".cz" / "MEMORY.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("content", "content changed externally")
    path.write_text(text, encoding="utf-8")
    warnings = store.write_memory(
        store.read_memory().replace("changed externally", "writer view"),
        expected_hashes={eid: h},
    )
    assert warnings
    assert (tmp_path / ".cz" / "MEMORY.conflicts.md").is_file()


def _lock_holder(lock_path: str, ready: multiprocessing.Event, release: multiprocessing.Event) -> None:
    import fcntl

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    ready.set()
    release.wait(timeout=5)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def test_lock_contention(tmp_path: Path) -> None:
    store = CzStore(tmp_path)
    store.init_scaffold()
    lock = str(store.lock_path)
    ready = multiprocessing.Event()
    release = multiprocessing.Event()
    proc = multiprocessing.Process(target=_lock_holder, args=(lock, ready, release))
    proc.start()
    assert ready.wait(timeout=3)
    # Second writer should block briefly then succeed when released
    release.set()
    store.memory_add("after lock", "ok")
    proc.join(timeout=3)
    assert proc.exitcode == 0


def test_pointer_idempotent(tmp_path: Path) -> None:
    from construct_zero.home.pointers import apply_pointers, remove_pointers

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    apply_pointers(tmp_path, assume_yes=True)
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    apply_pointers(tmp_path, assume_yes=True)
    assert agents == (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    removed = remove_pointers(tmp_path)
    assert "AGENTS.md" in removed
    assert "<!-- cz:home:start -->" not in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_git_exclude(tmp_path: Path) -> None:
    from construct_zero.home.pointers import git_exclude_cz

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    git_exclude_cz(tmp_path, commit_mode=False)
    exclude = (tmp_path / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".cz/" in exclude
    git_exclude_cz(tmp_path, commit_mode=False)
    assert exclude.count(".cz/") == 1
