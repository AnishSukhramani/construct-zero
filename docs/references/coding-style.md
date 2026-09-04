# Coding style for agents

Lean, surgical changes aligned with [.cursor/rules/00-governance.mdc](../../.cursor/rules/00-governance.mdc).

## Core principles

1. **Minimal diff** — solve the asked task only; no drive-by refactors.
2. **Match existing patterns** — naming, imports, test style in the target package.
3. **One subsystem per task** — read nested `AGENTS.md` before editing that tree.
4. **Verify in code** — never document or implement behavior you have not traced in source.
5. **Ask before** — new dependencies, `.gitignore` changes, Construct-Zero invariant changes, destructive shell.

## Where to edit (cheat sheet)

| Task | Primary paths |
|------|----------------|
| OpenAI API / streaming | `adapter/src/construct_zero/server.py`, `openai_types.py` |
| Cursor SDK / tools | `adapter/src/construct_zero/drivers/cursor.py`, `core/sessions.py` |
| Adapter config | `adapter/src/construct_zero/config.py`, `config/construct-zero.yaml.example` |
| Voice `/turn` flow | `voice/src/construct_zero_voice/server.py` |
| Hermes subprocess | `voice/src/construct_zero_voice/hermes_bridge.py` |
| VPL parsing / FSM | `vpl/src/construct_zero_vpl/parser.py`, `engine.py`, `intents.py` |
| Provider metadata | `hermes-plugin/model-providers/construct-zero/` |
| Bootstrap scripts | `scripts/setup.sh`, `ensure-hermes.sh` |
| Agent docs | `docs/features/`, nested `AGENTS.md` |

## Tests

| Layer | Location | Runner |
|-------|----------|--------|
| OSS unit tests | `adapter/tests/`, `voice/tests/`, `vpl/tests/` | `./private/scripts/run-tests.sh` |
| Local safety tests | `private/tests/` (gitignored) | same |
| Live Cursor / Hermes | Manual only | `./scripts/doctor.sh` |

Default pytest uses mocks — no `CURSOR_API_KEY`, no Hermes clone required.

## Anti-patterns

- Adding a second agent brain in Construct-Zero
- Committing secrets, `hermes/`, or `private/`
- Bloating root `AGENTS.md` — use `docs/` instead
- Copying gitignored `zzz-docs/` verbatim into committed docs
- Binding adapter/voice to `0.0.0.0` without explicit user request

## After material changes

Update affected [docs/features/](../features/) doc and [features/index.md](../features/index.md). See [docs-maintenance.mdc](../../.cursor/rules/docs-maintenance.mdc).
