"""gitleaks allowlist catches fixture secrets in config only."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitleaks_allowlists_env_example_pattern() -> None:
    text = (ROOT / ".gitleaks.toml").read_text()
    assert "CURSOR_API_KEY=unused" in text
    assert "env" in text and "example" in text


def test_fake_secret_marker_documented() -> None:
    """Fixture secret used in verify-staged tests is allowlisted for full-repo scans."""
    text = (ROOT / ".gitleaks.toml").read_text()
    assert "sk-real-secret-value" in text
