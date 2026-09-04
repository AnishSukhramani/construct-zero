# AGENTS.md — Agent table of contents

**Construct-Zero:** Hermes owns the agent loop and tools; this repo provides inference-only OpenAI adapter + voice sidecar on loopback.

```text
You / Gateway  →  Hermes  →  Construct-Zero :8765  →  Cursor cloud models
Voice browser  →  :8767  →  STT → Hermes → VPL → TTS
```

## Read order

1. This file (routing)
2. [.cursor/rules/00-governance.mdc](.cursor/rules/00-governance.mdc) — git, secrets, OSS scope
3. [.cursor/rules/construct-zero.mdc](.cursor/rules/construct-zero.mdc) — architecture invariants
4. **One** doc from [Documentation map](#documentation-map) for your task

When editing inside a subsystem, Cursor also loads that directory's `AGENTS.md`.

## Non-negotiables

- **Git:** User owns all mutating git ops — agents never `add`/`commit`/`push`/`pull`
- **Secrets:** Never in tracked files — `.env` and `~/.hermes/.env` only
- **Hermes upstream:** Gitignored `hermes/` — never commit
- **Construct-Zero:** Inference-only, loopback, Cursor `ask` never `agent`
- **Scope:** Minimal diffs — see [docs/references/coding-style.md](docs/references/coding-style.md)

## Documentation map

| Doc | Use when |
|-----|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System map, ports, primary files |
| [docs/features/index.md](docs/features/index.md) | Feature registry + out-of-scope list |
| [docs/features/adapter-inference.md](docs/features/adapter-inference.md) | Adapter, Cursor driver, tool loop |
| [docs/features/voice-sidecar.md](docs/features/voice-sidecar.md) | STT/TTS, `/turn`, Hermes bridge |
| [docs/features/voice-vpl.md](docs/features/voice-vpl.md) | Layered speech, FSM, navigation |
| [docs/features/hermes-plugin.md](docs/features/hermes-plugin.md) | Hermes `construct-zero` provider |
| [docs/architecture/boundaries.md](docs/architecture/boundaries.md) | OSS vs gitignored paths |
| [docs/decisions/](docs/decisions/) | ADRs — why choices were made |
| [docs/references/scripts.md](docs/references/scripts.md) | Which script to run |
| [PRE-COMMIT-CHECKLIST.md](PRE-COMMIT-CHECKLIST.md) | Test + commit + push flow (user runs) |

Full tree index: [docs/README.md](docs/README.md).

## Repo map

| Path | Role |
|------|------|
| `adapter/` | Construct-Zero FastAPI adapter (`construct_zero`) — `:8765` |
| `voice/` | Hold-to-talk sidecar — `:8767` |
| `vpl/` | Voice Presentation Layer (`construct-zero-vpl`) |
| `hermes-plugin/` | Declarative Hermes Construct-Zero provider |
| `docs/` | Agent knowledge base (this system) |
| `scripts/` | init, setup, start, doctor, update |
| `construct-zero` | Folder-local CLI (`start`, `doctor`, `init`, `chat`, `help`) |
| `install.sh` | Curl cwd bootstrap (folder-isolated) |
| `config/` | Examples + upstream lock pin |
| `hermes/` | **Local only** — upstream clone (gitignored) |
| `private/`, `zzz-docs/` | **Local only** — tests, research (gitignored) |

## Dev entrypoints

```bash
# New machine / blank folder (isolated install)
mkdir my-agent && cd my-agent
curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash

./construct-zero init                                  # already cloned
./construct-zero start                                 # adapter
./construct-zero chat                                  # talk to Hermes (not a global "hermes" command)
./construct-zero help                                  # command menu
./scripts/setup.sh && ./scripts/start-adapter.sh && ./scripts/doctor.sh   # manual path
./scripts/setup-voice.sh && ./scripts/start-voice.sh   # optional
```

Hermes default provider: `~/.hermes/config.yaml` → `provider: construct-zero`, `base_url: http://127.0.0.1:8765/v1`.

## Never commit

`hermes/`, `.hermes/`, `.construct-zero/`, `.venvs/`, `.env`, `config/construct-zero.yaml`, `private/`, `zzz-docs/`, `*.log`, `.claude/`

## Doc maintenance

After material subsystem changes, update affected `docs/features/` and registry. Rule: [.cursor/rules/docs-maintenance.mdc](.cursor/rules/docs-maintenance.mdc).

Human setup: [README.md](README.md).
