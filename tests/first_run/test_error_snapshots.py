"""First-run error message snapshots (expanded in follow-up commits)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_install_sh_documents_non_empty_folder() -> None:
    text = (ROOT / "install.sh").read_text()
    assert "not empty" in text.lower() or "not empty" in text
