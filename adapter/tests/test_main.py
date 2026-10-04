"""CLI entry smoke tests."""

from __future__ import annotations

from unittest.mock import patch

from construct_zero.__main__ import main


def test_main_invokes_run():
    with patch("construct_zero.server.run") as run:
        assert main(["--host", "127.0.0.1", "--port", "8765"]) == 0
        run.assert_called_once_with(host="127.0.0.1", port=8765, config_path=None)
