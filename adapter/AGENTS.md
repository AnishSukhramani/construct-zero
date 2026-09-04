# adapter/ — Construct-Zero inference layer

OpenAI-compatible FastAPI on `127.0.0.1:8765`. Package: `construct_zero`.

## Scope

- HTTP façade for Hermes `construct-zero` provider
- Cursor SDK driver (`mode=ask` only)
- Tool-call parking/resume for Hermes tool loop
- **Not** tool execution, not Hermes agent logic

## Key files

| File | Role |
|------|------|
| `src/construct_zero/server.py` | Routes |
| `src/construct_zero/drivers/cursor.py` | Cursor SDK + tool passthrough |
| `src/construct_zero/core/sessions.py` | Tool-loop sessions |
| `src/construct_zero/core/backend.py` | `InferenceBackend` protocol |
| `src/construct_zero/config.py` | Config load |

## Invariants

- Loopback bind; `cursor.mode: ask`
- See root [.cursor/rules/construct-zero.mdc](../.cursor/rules/construct-zero.mdc)

## Deep dive

[docs/features/adapter-inference.md](../docs/features/adapter-inference.md)

## Tests

```bash
cd adapter && source .venv/bin/activate && pytest -q
```

Or `./private/scripts/run-tests.sh --fast` from repo root.
