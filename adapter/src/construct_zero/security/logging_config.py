"""Logging setup with secret redaction."""

from __future__ import annotations

import logging
import os

from construct_zero.security.redact import redact


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(str(a)) if isinstance(a, str) else a for a in record.args)
        return True


def configure_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    redacting = RedactingFilter()
    for handler in root.handlers:
        handler.addFilter(redacting)
    root.addFilter(redacting)
    if os.environ.get("CZ_DEBUG_HTTP_BODIES", "").strip() not in {"1", "true", "yes"}:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
