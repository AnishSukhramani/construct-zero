"""Inference backend registry, capabilities, and optional routing."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from construct_zero.config import CZConfig
from construct_zero.core.backend import InferenceBackend
from construct_zero.core.sessions import SessionStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Capabilities:
    tools: bool
    streaming: str  # "native" | "buffered"
    vision: bool
    usage: bool
    max_context: int | None = None


@dataclass(frozen=True)
class BackendSpec:
    name: str
    aliases: tuple[str, ...] = ()
    capabilities: Capabilities = field(
        default_factory=lambda: Capabilities(
            tools=False, streaming="buffered", vision=False, usage=False
        )
    )
    extra_name: str | None = None
    config_key: str | None = None
    factory: Callable[[CZConfig, SessionStore], InferenceBackend] | None = None


_BACKENDS: dict[str, BackendSpec] = {}
_ALIASES: dict[str, str] = {}


def register(spec: BackendSpec) -> None:
    _BACKENDS[spec.name] = spec
    for alias in spec.aliases:
        _ALIASES[alias] = spec.name


def resolve(name: str) -> str:
    _register_builtins()
    key = (name or "").strip().lower()
    if not key:
        raise ValueError("Backend name is required")
    if key in _BACKENDS:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    valid = sorted(set(_BACKENDS) | set(_ALIASES))
    raise ValueError(f"Unknown inference backend {name!r}. Valid: {', '.join(valid)}")


def list_backend_names() -> list[str]:
    _register_builtins()
    return sorted(_BACKENDS.keys())


def capabilities_for(backend: InferenceBackend) -> Capabilities:
    cap = getattr(backend, "capabilities", None)
    if isinstance(cap, Capabilities):
        return cap
    spec = _BACKENDS.get(getattr(backend, "name", ""))
    if spec is not None:
        return spec.capabilities
    return Capabilities(tools=True, streaming="buffered", vision=False, usage=False)


def _lazy_cursor(cfg: CZConfig, sessions: SessionStore) -> InferenceBackend:
    from construct_zero.drivers.cursor import CursorDriver

    return CursorDriver(cfg, sessions=sessions)


def _lazy_mock(_cfg: CZConfig, sessions: SessionStore) -> InferenceBackend:
    from construct_zero.drivers.mock import MockDriver

    return MockDriver(sessions=sessions)


def _lazy_claude(_cfg: CZConfig, _sessions: SessionStore) -> InferenceBackend:
    from construct_zero.drivers.claude_code import ClaudeCodeDriver

    return ClaudeCodeDriver()


def _lazy_openai_compat(cfg: CZConfig, sessions: SessionStore) -> InferenceBackend:
    from construct_zero.drivers.openai_compat import OpenAICompatDriver

    return OpenAICompatDriver(cfg, sessions=sessions)


def _register_builtins() -> None:
    if _BACKENDS:
        return
    register(
        BackendSpec(
            name="cursor",
            aliases=("hcx", "construct-zero", "cz"),
            capabilities=Capabilities(
                tools=True,
                streaming="native",
                vision=False,
                usage=True,
                max_context=256_000,
            ),
            factory=_lazy_cursor,
        )
    )
    register(
        BackendSpec(
            name="mock",
            capabilities=Capabilities(
                tools=True,
                streaming="buffered",
                vision=False,
                usage=False,
            ),
            factory=_lazy_mock,
        )
    )
    register(
        BackendSpec(
            name="claude_code",
            aliases=("claude-code", "claude"),
            capabilities=Capabilities(
                tools=False,
                streaming="buffered",
                vision=False,
                usage=False,
            ),
            factory=_lazy_claude,
        )
    )
    register(
        BackendSpec(
            name="openai_compat",
            aliases=("byo", "company", "openai-compatible"),
            capabilities=Capabilities(
                tools=True,
                streaming="native",
                vision=False,
                usage=True,
            ),
            extra_name="openai_compat",
            config_key="openai_compat",
            factory=_lazy_openai_compat,
        )
    )
    # codex: stub only — not registered


def build(cfg: CZConfig, sessions: SessionStore, name: str | None = None) -> InferenceBackend:
    _register_builtins()
    backend_name = resolve(name or cfg.inference.backend or "cursor")
    spec = _BACKENDS[backend_name]
    if spec.factory is None:
        raise ValueError(f"Backend {backend_name!r} has no factory")
    try:
        return spec.factory(cfg, sessions)
    except ImportError as exc:
        from construct_zero.drivers.stub_backend import StubBackend

        hint = spec.extra_name or backend_name
        return StubBackend(
            name=backend_name,
            detail=f"Install dependencies for backend {backend_name!r}: {exc}. "
            f"Try: uv pip install -e 'adapter[{hint}]'",
        )


def parse_routed_model(model: str | None) -> tuple[str | None, str | None]:
    """If model is ``backend:model_id``, return (backend, model_id)."""
    if not model or ":" not in model:
        return None, model
    left, _, right = model.partition(":")
    if not left or not right:
        return None, model
    try:
        resolve(left)
    except ValueError:
        return None, model
    return left, right


def routing_enabled(cfg: CZConfig) -> bool:
    return bool(getattr(cfg.inference, "routing", False))
