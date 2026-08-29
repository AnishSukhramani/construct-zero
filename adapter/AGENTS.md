# adapter/ — HCX inference layer

OpenAI-compatible FastAPI on `127.0.0.1:8765`. Package: `hcx`.

## Scope

- HTTP façade for Hermes `hcx` provider
- Cursor SDK driver (`mode=ask` only)
- Tool-call parking/resume for Hermes tool loop
- **Not** tool execution, not Hermes agent logic

## Key files

| File | Role |
|------|------|
| `src/hcx/server.py` | Routes |
| `src/hcx/drivers/cursor.py` | Cursor SDK + tool passthrough |
| `src/hcx/core/sessions.py` | Tool-loop sessions |
| `src/hcx/core/backend.py` | `InferenceBackend` protocol |
| `src/hcx/config.py` | Config load |

## Invariants

- Loopback bind; `cursor.mode: ask`
- See root [.cursor/rules/hcx.mdc](../.cursor/rules/hcx.mdc)

## Deep dive

[docs/features/adapter-inference.md](../docs/features/adapter-inference.md)

## Tests

```bash
cd adapter && source .venv/bin/activate && pytest -q
```

Or `./private/scripts/run-tests.sh --fast` from repo root.
