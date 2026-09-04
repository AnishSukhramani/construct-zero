"""CZ_* environment variables with HCX_* fallback."""

from __future__ import annotations

import os
import warnings

_warned: set[str] = set()


def env_cz(suffix: str, default: str | None = None) -> str | None:
    """Read CZ_{suffix}, then legacy HCX_{suffix}."""
    cz = f"CZ_{suffix}"
    if cz in os.environ:
        return os.environ[cz]
    hcx = f"HCX_{suffix}"
    if hcx in os.environ:
        if hcx not in _warned:
            _warned.add(hcx)
            warnings.warn(
                f"{hcx} is deprecated; use {cz} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return os.environ[hcx]
    return default
