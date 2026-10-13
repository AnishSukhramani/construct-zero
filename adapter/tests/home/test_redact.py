from construct_zero.home.redact import redact


def test_redact_corpus() -> None:
    sample = """
    sk-1234567890123456789012345678901234567890
    sk-ant-api03-abcdefghijklmnopqrstuvwxyz
    Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test
    CURSOR_API_KEY=supersecret
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn
    -----END RSA PRIVATE KEY-----
    """
    out = redact(sample)
    assert "sk-1234567890" not in out
    assert "sk-ant-api03" not in out
    assert "supersecret" not in out
    assert "BEGIN RSA PRIVATE KEY" not in out
    assert "[REDACTED" in out
