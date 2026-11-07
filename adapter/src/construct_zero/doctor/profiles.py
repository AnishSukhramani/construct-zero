"""Certification profiles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckSpec:
    id: str
    severity: str  # required | advisory
    description: str
    fix: str


CZ_CERTIFIED_V1: tuple[CheckSpec, ...] = (
    CheckSpec(
        "os",
        "required",
        "Supported OS",
        "Use macOS 13+ or Linux x86_64/arm64 (or WSL2 on Windows).",
    ),
    CheckSpec(
        "wsl", "advisory", "WSL environment", "See docs/recipes/wsl.md for Windows via WSL2."
    ),
    CheckSpec("python", "required", "Python version", "Use Python 3.10–3.12 (3.12 recommended)."),
    CheckSpec(
        "uv-lock", "advisory", "Locked adapter deps", "Run: cd adapter && uv sync --all-groups"
    ),
    CheckSpec("adapter-bind", "required", "Loopback bind", "Set adapter.host to 127.0.0.1 only."),
    CheckSpec(
        "health",
        "required",
        "Adapter /health",
        "Run ./construct-zero start and fix /health detail.",
    ),
    CheckSpec(
        "backend", "required", "Backend + ask mode", "Set inference.backend and cursor.mode: ask."
    ),
    CheckSpec("models", "required", "/v1/models", "Ensure backend lists at least one model."),
    CheckSpec(
        "chat", "required", "Chat round trip", "Set CURSOR_API_KEY or use mock backend for smoke."
    ),
    CheckSpec("tools", "required", "Tool round trip", "Use a tool-capable backend (cursor/mock)."),
    CheckSpec(
        "hermes-pin",
        "required",
        "Hermes pin",
        "Run ./scripts/update-hermes.sh to match upstream.lock.yaml.",
    ),
    CheckSpec(
        "hermes-plugin",
        "required",
        "Hermes plugin",
        "Run ./construct-zero init and verify plugin symlink.",
    ),
    CheckSpec(
        "hermes-config",
        "required",
        "Hermes provider config",
        "Set provider construct-zero and base_url http://127.0.0.1:PORT/v1.",
    ),
    CheckSpec(
        "client:cline",
        "advisory",
        "Cline client checks",
        "Run ./construct-zero doctor --client=cline.",
    ),
    CheckSpec(
        "errors",
        "advisory",
        "Fix-message catalog",
        "Re-run ./scripts/setup.sh if doctor snapshots drift.",
    ),
    CheckSpec(
        "secrets-hygiene",
        "required",
        "Secrets hygiene",
        "Keep .env mode 600; never put CURSOR_API_KEY in config/*.yaml.",
    ),
    CheckSpec(
        "project-isolation",
        "required",
        "Project vs CZ install root",
        "Set CZ_PROJECT_ROOT to your app repo; use nested construct-zero/ or gitignored .cz/.",
    ),
    CheckSpec(
        "adapter-auth",
        "advisory",
        "Optional adapter bearer",
        "Set adapter.api_key (or CZ_API_KEY) for defense in depth on loopback.",
    ),
)
