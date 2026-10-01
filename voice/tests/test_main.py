"""Voice CLI smoke test."""

from __future__ import annotations

from unittest.mock import patch

from construct_zero_voice.__main__ import main


def test_voice_main_invokes_run():
    with patch("construct_zero_voice.server.run") as run:
        assert main(["--port", "8767"]) == 0
        run.assert_called_once_with(host=None, port=8767)
