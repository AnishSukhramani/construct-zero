# HCX adapter — inference layer

OpenAI-compatible FastAPI service on `127.0.0.1:8765`. Hermes calls it as model provider `hcx`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Adapter + Cursor SDK status |
| GET | `/v1/models` | Models from Cursor |
| POST | `/v1/chat/completions` | Chat (stream + tools) |

## Key modules

| Module | Role |
|--------|------|
| [server.py](../../adapter/src/hcx/server.py) | FastAPI app, routes |
| [drivers/cursor.py](../../adapter/src/hcx/drivers/cursor.py) | Cursor SDK, `ask` mode, tool parking |
| [core/sessions.py](../../adapter/src/hcx/core/sessions.py) | Tool-loop session store |
| [core/backend.py](../../adapter/src/hcx/core/backend.py) | `InferenceBackend` protocol |
| [config.py](../../adapter/src/hcx/config.py) | YAML + env config load |
| [drivers/claude_code.py](../../adapter/src/hcx/drivers/claude_code.py) | **Stub** — do not implement without ask |

## Tool passthrough (Phase 2)

1. Hermes sends `tools` in chat completion request.
2. CursorDriver maps them to SDK `custom_tools`.
3. When Cursor returns tool calls, adapter parks them and responds with OpenAI-shaped `tool_calls`.
4. Hermes executes tools, sends tool results; adapter resumes parked Cursor run.

Tests: [adapter/tests/test_tool_loop.py](../../adapter/tests/test_tool_loop.py), [adapter/tests/test_api.py](../../adapter/tests/test_api.py) (FakeBackend).

## Config

- Example: [config/hermesxcursor.yaml.example](../../config/hermesxcursor.yaml.example)
- Local (gitignored): `config/hermesxcursor.yaml`, `~/.hermesxcursor/config.yaml`
- **Must keep** `inference.cursor.mode: ask`

## What not to build here

- Terminal, web, file, or skill execution (Hermes)
- Cursor `agent` mode or Cursor native tools
- Public `:8765` bind
- Dependency on vendored Hermes source in repo

## Tests

```bash
cd adapter && source .venv/bin/activate && pytest -q
```

Or local harness: `./private/scripts/run-tests.sh --fast`

## Related

- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [ADR 001](../decisions/001-inference-only-ask-mode.md)
- [adapter/AGENTS.md](../../adapter/AGENTS.md)
