"""Secret redaction corpus tests."""

from __future__ import annotations

from construct_zero.security.redact import redact, redact_exception_message, redact_mapping


def test_redact_api_and_cloud_keys() -> None:
    sample = """
    sk-1234567890123456789012345678901234567890
    sk-ant-api03-abcdefghijklmnopqrstuvwxyz
    ghp_1234567890123456789012345678901234abcd
    {slack_fixture}
    AKIAIOSFODNN7EXAMPLE
    Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test.sig
    CURSOR_API_KEY=supersecret
    mongodb+srv://user:pass@cluster.example.net/db
    api_key: "abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    """
    out = redact(sample)
    assert "supersecret" not in out
    assert "ghp_1234567890" not in out
    assert "pass@cluster" not in out
    assert "[REDACTED" in out


def test_redact_mapping_and_exception() -> None:
    mapped = redact_mapping(
        {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.abc.def"}
    )
    assert "eyJhbGci" not in str(mapped)
    msg = redact_exception_message(RuntimeError("CURSOR_API_KEY=supersecret"))
    assert "supersecret" not in msg


def test_redact_pem_block() -> None:
    pem = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn
-----END RSA PRIVATE KEY-----"""
    out = redact(pem)
    assert "BEGIN RSA PRIVATE KEY" not in out
