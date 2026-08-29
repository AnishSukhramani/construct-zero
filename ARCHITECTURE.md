# Architecture — HCX (Hermes on Cursor)

One-page map. Details live in [docs/features/](docs/features/) and subsystem `AGENTS.md` files.

## Core invariant

**Hermes owns the agent loop and all tools.** HCX is **inference-only**: an OpenAI-compatible adapter on loopback that bills Cursor subscription models. Cursor driver mode is **`ask`**, never `agent`.

## Primary data flows

### Text / CLI / Gateway path

```text
User / Gateway  →  Hermes (tools, memory, skills)
                        ↓  OpenAI HTTP
                   HCX adapter :8765
                        ↓  cursor-sdk
                   Cursor cloud models
```

### Voice hold-to-talk path

```text
Browser :8767  →  STT (faster-whisper)
              →  hermes chat -q  (via HCX provider)
              →  full reply text
              →  VPL (layered speech, zero extra LLM)
              →  TTS (Kokoro)
```

Screen shows **full canonical text**; TTS speaks **verbatim excerpts** from source spans only.

## Packages

| Package | Port | Role |
|---------|------|------|
| [adapter/](../adapter/) | `127.0.0.1:8765` | OpenAI façade + CursorDriver |
| [voice/](../voice/) | `127.0.0.1:8767` | STT/TTS + Hermes bridge + VPL wiring |
| [vpl/](../vpl/) | (library) | Voice Presentation Layer |
| [hermes-plugin/](../hermes-plugin/) | — | Declarative Hermes `hcx` provider |
| `hermes/` | — | **Local only** — upstream clone (gitignored) |

## Primary source anchors

| Concern | File |
|---------|------|
| FastAPI adapter routes | [adapter/src/hcx/server.py](../adapter/src/hcx/server.py) |
| Cursor SDK driver, tool parking | [adapter/src/hcx/drivers/cursor.py](../adapter/src/hcx/drivers/cursor.py) |
| Tool-loop sessions | [adapter/src/hcx/core/sessions.py](../adapter/src/hcx/core/sessions.py) |
| Backend protocol | [adapter/src/hcx/core/backend.py](../adapter/src/hcx/core/backend.py) |
| Voice `/turn`, VPL integration | [voice/src/hcx_voice/server.py](../voice/src/hcx_voice/server.py) |
| Hermes subprocess bridge | [voice/src/hcx_voice/hermes_bridge.py](../voice/src/hcx_voice/hermes_bridge.py) |
| VPL engine + FSM | [vpl/src/hcx_vpl/engine.py](../vpl/src/hcx_vpl/engine.py) |
| Provider registration | [hermes-plugin/model-providers/hcx/__init__.py](../hermes-plugin/model-providers/hcx/__init__.py) |

## Invariants (do not violate)

See [.cursor/rules/hcx.mdc](../.cursor/rules/hcx.mdc):

- Loopback bind only — do not expose `:8765` / `:8767` publicly
- `cursor.mode: ask` — Hermes executes tools, not Cursor
- Hermes upstream in gitignored `hermes/` — not vendored

## Runtime outside this repo

| Location | Contents |
|----------|----------|
| `~/.hermes/` | Hermes config, skills, memory, plugins symlink |
| `~/.hermesxcursor/` | Adapter supervisor PID/log, optional adapter config |
| `.venvs/hermes/` | Hermes CLI venv (from `./scripts/setup.sh`) |

## Further reading

- [docs/architecture/data-flow.md](docs/architecture/data-flow.md)
- [docs/architecture/boundaries.md](docs/architecture/boundaries.md)
- [docs/features/index.md](docs/features/index.md)
