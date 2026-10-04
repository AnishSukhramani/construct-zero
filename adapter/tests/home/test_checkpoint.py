from pathlib import Path

from construct_zero.home.checkpoint import Checkpoint, parse_checkpoint, write_checkpoint


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    cp = Checkpoint(
        from_agent="claude-code",
        reason="manual",
        goal="Fix bug",
        next_step="Run tests",
    )
    md = cp.to_markdown()
    parsed = parse_checkpoint(md)
    assert parsed is not None
    assert parsed.goal == "Fix bug"
    write_checkpoint(tmp_path, cp)
    assert (tmp_path / ".cz" / "checkpoint.md").is_file()
    assert list((tmp_path / ".cz" / "handoffs").glob("*.md"))
