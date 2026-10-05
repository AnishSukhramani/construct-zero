from construct_zero.home.quota import match_quota, strip_ansi


def test_quota_patterns() -> None:
    assert match_quota("claude-code", "You hit the 5-hour limit today")
    assert match_quota("cursor", "You've hit your usage limit")
    assert not match_quota("claude-code", "all good")
    assert strip_ansi("\x1b[31musage limit reached\x1b[0m") == "usage limit reached"
