# Architecture — Construct-Zero

One-page map. Details live in [docs/features/](docs/features/) and subsystem `AGENTS.md` files.

## Core invariant

**Hermes owns the agent loop and all tools.** Construct-Zero is **inference-only**: an OpenAI-compatible adapter on loopback that bills Cursor subscription models. Cursor driver mode is **`ask`**, never `agent`.

## Primary data flows

### Text / CLI / Gateway path

```text
User / Gateway  →  Hermes (tools, memory, skills)
                        ↓  OpenAI HTTP
                   Construct-Zero adapter :8765
                        ↓  cursor-sdk
                   Cursor cloud models
```

### Voice hold-to-talk path

```text
Browser :8767  →  STT (faster-whisper)
              →  hermes chat -q  (via construct-zero provider)
              →  full reply text
              →  VPL (layered speech, zero extra LLM)
              →  TTS (Kokoro)
```

Screen shows **full canonical text**; TTS speaks **verbatim excerpts** from source spans only.

## Packages

| Package | Port | Role |
|---------|------|------|
| [adapter/](adapter/) | `127.0.0.1:8765` | OpenAI façade + CursorDriver |
| [voice/](voice/) | `127.0.0.1:8767` | STT/TTS + Hermes bridge + VPL wiring |
| [vpl/](vpl/) | (library) | Voice Presentation Layer |
| [hermes-plugin/](hermes-plugin/) | — | Declarative Hermes `construct-zero` provider |
| `hermes/` | — | **Local only** — upstream clone (gitignored) |

## Primary source anchors

| Concern | File |
|---------|------|
| FastAPI adapter routes | [adapter/src/construct_zero/server.py](adapter/src/construct_zero/server.py) |
| Cursor SDK driver, tool parking | [adapter/src/construct_zero/drivers/cursor.py](adapter/src/construct_zero/drivers/cursor.py) |
| Tool-loop sessions | [adapter/src/construct_zero/core/sessions.py](adapter/src/construct_zero/core/sessions.py) |
| Backend protocol | [adapter/src/construct_zero/core/backend.py](adapter/src/construct_zero/core/backend.py) |
| Voice `/turn`, VPL integration | [voice/src/construct_zero_voice/server.py](voice/src/construct_zero_voice/server.py) |
| Hermes subprocess bridge | [voice/src/construct_zero_voice/hermes_bridge.py](voice/src/construct_zero_voice/hermes_bridge.py) |
| VPL engine + FSM | [vpl/src/construct_zero_vpl/engine.py](vpl/src/construct_zero_vpl/engine.py) |
| Provider registration | [hermes-plugin/model-providers/construct-zero/__init__.py](hermes-plugin/model-providers/construct-zero/__init__.py) |

## Invariants (do not violate)

See [.cursor/rules/construct-zero.mdc](.cursor/rules/construct-zero.mdc):

- Loopback bind only — do not expose `:8765` / `:8767` publicly
- `cursor.mode: ask` — Hermes executes tools, not Cursor
- Hermes upstream in gitignored `hermes/` — not vendored

## Runtime outside this repo

| Location | Contents |
|----------|----------|
| `~/.hermes/` | Hermes config, skills, memory, plugins symlink |
| `~/.construct-zero/` | Adapter supervisor PID/log, optional adapter config |
| `.venvs/hermes/` | Hermes CLI venv (from `./scripts/setup.sh`) |

## Further reading

- [docs/architecture/data-flow.md](docs/architecture/data-flow.md)
- [docs/architecture/boundaries.md](docs/architecture/boundaries.md)
- [docs/features/index.md](docs/features/index.md)
- [ADR 004](docs/decisions/004-construct-zero-rename.md) — rebrand and shim policy
