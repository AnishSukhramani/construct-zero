"""Optional Cursor Agent CLI / ACP helpers for tool-bearing requests.

Primary tool passthrough uses cursor-sdk custom_tools (see cursor.py).
This module detects an agent binary and can spawn ACP for future hardening.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass
class AcpAvailability:
    available: bool
    binary: str | None = None
    detail: str = ""


def resolve_agent_bin(explicit: str = "") -> str | None:
    if explicit:
        return explicit if shutil.which(explicit) or os.path.isfile(explicit) else None
    for name in ("cursor-agent", "agent"):
        path = shutil.which(name)
        if path:
            return path
    return None


def check_acp(explicit: str = "") -> AcpAvailability:
    binary = resolve_agent_bin(explicit)
    if not binary:
        return AcpAvailability(
            available=False,
            detail="cursor-agent/agent not on PATH; SDK custom_tools path used for tools",
        )
    return AcpAvailability(
        available=True,
        binary=binary,
        detail=f"ACP binary available at {binary}",
    )
