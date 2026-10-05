"""ACP binary detection (no real agent required)."""

from __future__ import annotations

from construct_zero.drivers.acp import check_acp, resolve_agent_bin


def test_resolve_missing_binary():
    assert resolve_agent_bin("definitely-not-a-real-binary-name-xyz") is None


def test_check_acp_without_agent():
    status = check_acp("")
    assert status.available is False
    assert "SDK custom_tools" in status.detail


def test_check_acp_with_explicit_path(tmp_path):
    script = tmp_path / "fake-agent"
    script.write_text("#!/bin/sh\necho ok\n")
    script.chmod(0o755)
    status = check_acp(str(script))
    assert status.available is True
    assert status.binary == str(script)
