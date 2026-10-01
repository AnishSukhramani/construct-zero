"""install.sh empty-folder detection (_non_dot_entries) matches legacy semantics."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Keep in sync with install.sh _non_dot_entries (SC2010-free glob version).
_BASH = r"""
_non_dot_entries() {
  local entry
  for entry in "$INSTALL_DIR"/* "$INSTALL_DIR"/.[!.]* "$INSTALL_DIR"/..?*; do
    [[ -e "$entry" ]] || continue
    local base
    base="$(basename "$entry")"
    [[ "$base" == ".DS_Store" ]] && continue
    printf '%s\n' "$base"
  done
}
INSTALL_DIR="$1"
_non_dot_entries
"""


def _entries(tmp: Path) -> list[str]:
    r = subprocess.run(
        ["bash", "-c", _BASH, "_", str(tmp)],
        text=True,
        capture_output=True,
        check=True,
    )
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def test_ds_store_only_is_empty(tmp_path: Path) -> None:
    (tmp_path / ".DS_Store").write_text("")
    assert _entries(tmp_path) == []


def test_real_file_is_not_empty(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("hi")
    assert _entries(tmp_path) == ["readme.txt"]


def test_dotfile_other_than_ds_store_counts(tmp_path: Path) -> None:
    (tmp_path / ".gitkeep").write_text("")
    assert _entries(tmp_path) == [".gitkeep"]
