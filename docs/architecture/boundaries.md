# System boundaries

## What this repo ships (OSS product)

| Path | Agent may edit | Commit |
|------|----------------|--------|
| `adapter/` | Yes | Yes |
| `voice/` | Yes | Yes |
| `vpl/` | Yes | Yes |
| `hermes-plugin/` | Yes | Yes |
| `scripts/` | Yes | Yes |
| `config/*.example`, `config/upstream.lock.yaml` | Yes | Yes |
| `docs/`, `AGENTS.md`, `ARCHITECTURE.md` | Yes | Yes |
| `.cursor/rules/` | Yes | Yes |

## Local only — never commit

| Path | Purpose |
|------|---------|
| `hermes/` | Upstream Hermes git clone |
| `.venvs/`, `adapter/.venv/`, `private/.venv/` | Python virtualenvs |
| `.env`, `config/hermesxcursor.yaml` | Secrets / local adapter config |
| `private/` | Local test harness + scratch |
| `zzz-docs/` | Private research (distill into `docs/`, do not copy wholesale) |
| `*.log`, `.claude/` | Runtime / IDE local |

## Outside the repo entirely

| Location | Purpose |
|----------|---------|
| `~/.hermes/` | Hermes runtime: config, skills, memory, plugins |
| `~/.hermesxcursor/` | Adapter supervisor state |

Agents must **not** move `~/.hermes` content into the repo for convenience.

## Responsibility split

| Component | Owns |
|-----------|------|
| **Hermes** (upstream) | Agent loop, tools, gateway, skills, memory |
| **HCX adapter** | OpenAI HTTP, Cursor inference, tool-call passthrough |
| **Voice sidecar** | STT/TTS, browser UI, Hermes bridge orchestration |
| **VPL** | Post-hoc speech structuring (no LLM) |
| **Hermes plugin** | Provider declaration pointing at HCX base URL |

## Git policy

User owns all mutating git operations. Agents: read-only `git status` / `diff` / `log` only. See [00-governance.mdc](../../.cursor/rules/00-governance.mdc).
