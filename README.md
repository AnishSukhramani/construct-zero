# HCX — Hermes on Cursor

Run [Hermes Agent](https://github.com/NousResearch/hermes-agent) at full capability while **Cursor subscription pays for inference** (`auto` and other Cursor models). No OpenRouter / OpenAI / Ollama required for the main path.

## Invariant

Hermes owns the agent loop and all tools. HCX is an **inference-only** OpenAI-compatible adapter on `127.0.0.1:8765`. Cursor driver mode stays `ask` — never a second agent brain.

```text
You / Gateway  →  Hermes  →  HCX :8765  →  Cursor cloud models
```

## Repo layout

| Path | Role |
|------|------|
| `hermes/` | **Local only** — Hermes upstream clone (gitignored; created by `./scripts/setup.sh`) |
| [`adapter/`](adapter/) | **HCX** FastAPI adapter (`hcx` package) |
| [`voice/`](voice/) | Hold-to-talk sidecar (STT/TTS + Hermes bridge) on `:8767` |
| [`vpl/`](vpl/) | Voice Presentation Layer (`hcx-vpl`) — layered spoken delivery, zero extra LLM |
| [`hermes-plugin/model-providers/hcx/`](hermes-plugin/model-providers/hcx/) | Declarative Hermes provider |
| [`config/upstream.lock.yaml`](config/upstream.lock.yaml) | Recommended Hermes git pin |
| [`config/hermesxcursor.yaml.example`](config/hermesxcursor.yaml.example) | Adapter config |
| [`scripts/`](scripts/) | setup, start, doctor, update, voice |

## Requirements

- Git, curl, Python 3.11+ (3.12 preferred)
- [uv](https://github.com/astral-sh/uv) optional but recommended
- `CURSOR_API_KEY` from [Cursor dashboard](https://cursor.com/dashboard) → API Keys
- Voice: `ffmpeg` (and often `espeak-ng` for Kokoro)

## Quick start

```bash
git clone https://github.com/AnishSukhramani/construct-zero.git
cd construct-zero

# Cursor API key — copy .env.example or export in shell
cp .env.example .env   # edit CURSOR_API_KEY
export CURSOR_API_KEY=crsr_...
export HCX_API_KEY=unused   # if Hermes provider requires it

# Clone Hermes into gitignored hermes/ + adapter venv + plugin (see config/upstream.lock.yaml)
./scripts/setup.sh

# Start adapter (loopback, auto-restart supervisor)
./scripts/start-adapter.sh

# Health + smoke chat
./scripts/doctor.sh

# Hermes CLI (installed by setup into .venvs/hermes)
.venvs/hermes/bin/hermes chat -q "Reply PONG" --provider hcx --model auto
```

Hermes config snippet (`~/.hermes/config.yaml`):

```yaml
model:
  provider: hcx
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

Future backends implement `InferenceBackend` (`adapter/src/hcx/core/backend.py`). `ClaudeCodeDriver` is a stub.

## Voice (hold-to-talk)

Browser push-to-talk on `127.0.0.1:8767` — press and hold to speak, release to send. Uses local **faster-whisper** (STT) + **Kokoro** (TTS), then `hermes chat -q` via HCX. Does not replace Hermes CLI `/voice` (Ctrl+B); this is the web / VPS-friendly path.

**Layered delivery (VPL):** Long Hermes replies are parsed extractively by [`vpl/`](vpl/) (`hcx-vpl`). The full markdown answer stays on screen unchanged; TTS speaks orient → map → deepen layers using verbatim source spans. Navigation turns (`second`, bucket names, `read all`, etc.) reuse the stored session and **do not call Hermes again**. Short answers pass through unchanged.

```bash
# Adapter must already be up
./scripts/start-adapter.sh

./scripts/setup-voice.sh   # installs vpl + voice editable
./scripts/start-voice.sh
# open http://127.0.0.1:8767/
```

Optional VPL env vars (see `.env.example`): `HCX_VPL_ENABLED`, `HCX_VPL_LAYER_THRESHOLD_ITEMS`, `HCX_VPL_MAX_BUCKETS`, `HCX_VPL_PASSTHROUGH_MAX_WORDS`, `HCX_VPL_SESSION_TTL_SEC`.

Requires `ffmpeg` (and often `espeak-ng` for Kokoro). First run downloads Whisper + Kokoro weights. On a VPS, keep the sidecar on loopback and tunnel:

```bash
ssh -L 8767:127.0.0.1:8767 user@vps
```

See [`config/voice.profile.yaml.example`](config/voice.profile.yaml.example) for optional Hermes TTS wiring to the sidecar.

## Updating

**HCX (this repo):**

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
3. Hermes updatable via `./scripts/update-hermes.sh` without rewriting HCX  
4. Owned surface: OpenAI façade + CursorDriver + Hermes plugin + doctor/harness  

## Out of scope (for now)

- Depending on `cursor-api-proxy` as runtime  
- Claude Code driver implementation  
- Public exposure of the adapter port  
- Cursor Cloud / iOS profiles  

## For maintainers

**Agents:** start at [`AGENTS.md`](AGENTS.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md). Deploy flow: [`PRE-COMMIT-CHECKLIST.md`](PRE-COMMIT-CHECKLIST.md).

`hermes/`, `.venvs/`, `.env`, `config/hermesxcursor.yaml`, `zzz-docs/`, and `private/` are gitignored. After `./scripts/setup.sh`, **`git add .` is safe** — Hermes source is never committed.

Before your first push, verify nothing sensitive is staged:

```bash
git add .
git diff --cached --name-only | rg '^hermes/'    # must print nothing
git diff --cached --name-only | rg '^(\.env$|\.venvs/|zzz-docs/)'  # must print nothing
git status   # ~50 files, all HCX-owned paths
```

On GitHub, confirm there is no `hermes/` folder in the repo tree.

## License

HCX adapter, voice sidecar, and plugin: MIT (this repo). [Hermes Agent](https://github.com/NousResearch/hermes-agent) is upstream under its own license (cloned locally into gitignored `hermes/`).
