# Construct-Zero

Run [Hermes Agent](https://github.com/NousResearch/hermes-agent) at full capability while **Cursor subscription pays for inference** (`auto` and other Cursor models). No OpenRouter / OpenAI / Ollama required for the main path.

## Invariant

Hermes owns the agent loop and all tools. Construct-Zero is an **inference-only** OpenAI-compatible adapter on `127.0.0.1:8765`. Cursor driver mode stays `ask` — never a second agent brain.

```text
You / Gateway  →  Hermes  →  Construct-Zero :8765  →  Cursor cloud models
```

## Repo layout

| Path | Role |
|------|------|
| `hermes/` | **Local only** — Hermes upstream clone (gitignored; created by `./scripts/setup.sh`) |
| [`adapter/`](adapter/) | **Construct-Zero** FastAPI adapter (`construct_zero` package) |
| [`voice/`](voice/) | Hold-to-talk sidecar (STT/TTS + Hermes bridge) on `:8767` |
| [`vpl/`](vpl/) | Voice Presentation Layer (`construct-zero-vpl`) — layered spoken delivery, zero extra LLM |
| [`hermes-plugin/model-providers/construct-zero/`](hermes-plugin/model-providers/construct-zero/) | Declarative Hermes provider |
| [`config/upstream.lock.yaml`](config/upstream.lock.yaml) | Recommended Hermes git pin |
| [`config/construct-zero.yaml.example`](config/construct-zero.yaml.example) | Adapter config |
| [`scripts/`](scripts/) | init, install, setup, start, doctor, update, voice |

## Requirements

- Git, curl, Python 3.11+ (3.12 preferred)
- [uv](https://docs.astral.sh/uv/) is offered during `install.sh` / `./scripts/init.sh` (recommended; no Homebrew required)
- `CURSOR_API_KEY` from [Cursor dashboard](https://cursor.com/dashboard) → API Keys
- Voice: `ffmpeg` (and often `espeak-ng` for Kokoro)

## Quick start

Each folder is its own install (Hermes home, adapter state, and ports stay inside that directory).

```bash
mkdir my-agent && cd my-agent
curl -fsSL https://raw.githubusercontent.com/AnishSukhramani/construct-zero/main/install.sh | bash
```

That clones this repo into the current folder, asks a few setup questions, and does not touch other Construct-Zero copies on the same machine.

Contributor / already-cloned path:

```bash
git clone https://github.com/AnishSukhramani/construct-zero.git
cd construct-zero
./scripts/init.sh

# Or manual:
cp .env.example .env   # edit CURSOR_API_KEY
export CURSOR_API_KEY=crsr_...
./scripts/setup.sh
./scripts/start-adapter.sh
./scripts/doctor.sh
```

After init, daily use:

```bash
./scripts/start.sh              # adapter (+ --voice if set up)
./scripts/doctor.sh
.venvs/hermes/bin/hermes chat -q "Reply PONG" --provider construct-zero --model auto
```

Hermes config for a cwd install lives in `.hermes/config.yaml` inside that folder (`base_url` uses the port written to `.env`). Global default remains `~/.hermes/config.yaml` when you run `./scripts/init.sh` without `install.sh`:

```yaml
model:
  provider: construct-zero
  default: auto
  base_url: http://127.0.0.1:8765/v1
```

## Adapter API

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Adapter + Cursor SDK status |
| `GET /v1/models` | Models from `Cursor.models.list()` |
| `POST /v1/chat/completions` | Chat (+ tools, stream) |

**Phase 1:** text chat via `cursor-sdk` with `tools=[]` (no Cursor built-in tools).  
**Phase 2:** Hermes `tools` exposed as SDK `custom_tools`; calls are parked and returned as OpenAI `tool_calls` so **Hermes executes** them; tool results resume the same run.

Future backends implement `InferenceBackend` (`adapter/src/construct_zero/core/backend.py`). `ClaudeCodeDriver` is a stub.

## Voice (hold-to-talk)

Browser push-to-talk on `127.0.0.1:8767` — press and hold to speak, release to send. Uses local **faster-whisper** (STT) + **Kokoro** (TTS), then `hermes chat -q` via Construct-Zero. Does not replace Hermes CLI `/voice` (Ctrl+B); this is the web / VPS-friendly path.

**Layered delivery (VPL):** Long Hermes replies are parsed extractively by [`vpl/`](vpl/) (`construct-zero-vpl`). The full markdown answer stays on screen unchanged; TTS speaks orient → map → deepen layers using verbatim source spans. Navigation turns (`second`, bucket names, `read all`, etc.) reuse the stored session and **do not call Hermes again**. Short answers pass through unchanged.

```bash
# Adapter must already be up
./scripts/start-adapter.sh

./scripts/setup-voice.sh   # installs vpl + voice editable
./scripts/start-voice.sh
# open http://127.0.0.1:8767/
```

Optional VPL env vars (see `.env.example`): `CZ_VPL_ENABLED`, `CZ_VPL_LAYER_THRESHOLD_ITEMS`, `CZ_VPL_MAX_BUCKETS`, `CZ_VPL_PASSTHROUGH_MAX_WORDS`, `CZ_VPL_SESSION_TTL_SEC`.

Requires `ffmpeg` (and often `espeak-ng` for Kokoro). First run downloads Whisper + Kokoro weights. On a VPS, keep the sidecar on loopback and tunnel:

```bash
ssh -L 8767:127.0.0.1:8767 user@vps
```

See [`config/voice.profile.yaml.example`](config/voice.profile.yaml.example) for optional Hermes TTS wiring to the sidecar.

## Updating

**Construct-Zero (this repo):**

```bash
git pull
```

**Hermes (upstream, in gitignored `hermes/`):**

```bash
./scripts/update-hermes.sh           # latest main
./scripts/update-hermes.sh <sha>     # pin a commit
```

After `git pull`, if [`config/upstream.lock.yaml`](config/upstream.lock.yaml) changed, run `./scripts/update-hermes.sh` to match the new pin.

Hermes runtime data (skills, memory, config) stays in `~/.hermes` — separate from the upstream clone in `hermes/`.

## Tests

```bash
cd adapter && source .venv/bin/activate && pytest -q

# VPL (no ML deps)
cd ../vpl && pip install -e '.[dev]' && pytest -q

# Voice (mocked STT/TTS; no model download — install vpl first)
cd ../voice && source ../.venvs/voice/bin/activate && pytest -q
```

## Success criteria (MVP)

1. No external LLM API key for main Hermes chat  
2. Hermes tools work via Cursor Auto (tool passthrough)  
3. Hermes updatable via `./scripts/update-hermes.sh` without rewriting Construct-Zero  
4. Owned surface: OpenAI façade + CursorDriver + Hermes plugin + doctor/harness  

## Out of scope (for now)

- Depending on `cursor-api-proxy` as runtime  
- Claude Code driver implementation  
- Public exposure of the adapter port  
- Cursor Cloud / iOS profiles  

## Migration from HCX

This project was previously named **HCX — Hermes on Cursor**. Old names still work for one release:

- Hermes `--provider hcx` is an alias of `construct-zero`
- `HCX_*` env vars are read if the matching `CZ_*` var is unset
- `~/.hermesxcursor/` and `config/hermesxcursor.yaml` remain in the config search path

Prefer `CZ_*`, `~/.construct-zero/`, and `provider: construct-zero` in new setups. After pulling, re-run `./scripts/setup.sh` and `./scripts/setup-voice.sh` so editable packages pick up the rename.

## For maintainers

**Agents:** start at [`AGENTS.md`](AGENTS.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md). Deploy flow: [`PRE-COMMIT-CHECKLIST.md`](PRE-COMMIT-CHECKLIST.md).

`hermes/`, `.venvs/`, `.env`, `config/construct-zero.yaml`, `zzz-docs/`, and `private/` are gitignored. After `./scripts/setup.sh`, **`git add .` is safe** — Hermes source is never committed.

Before your first push, verify nothing sensitive is staged:

```bash
git add .
git diff --cached --name-only | rg '^hermes/'    # must print nothing
git diff --cached --name-only | rg '^(\.env$|\.venvs/|zzz-docs/)'  # must print nothing
git status   # Construct-Zero-owned paths only
```

On GitHub, confirm there is no `hermes/` folder in the repo tree.

## License

Construct-Zero adapter, voice sidecar, and plugin: MIT (this repo). [Hermes Agent](https://github.com/NousResearch/hermes-agent) is upstream under its own license (cloned locally into gitignored `hermes/`).
