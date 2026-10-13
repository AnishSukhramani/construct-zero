# Backend conformance matrix

Hermes-free checks that each inference backend exposes a minimal OpenAI-compatible surface:

- `GET /health` → `status: ok`
- `POST /v1/chat/completions` (non-stream) → HTTP 200 + assistant message

| Backend | CI expectation |
|---------|----------------|
| `mock` | **Pass** — deterministic test/first-run backend |
| `cursor` | **Pass** — uses in-process `fake_cursor_sdk` (no network) |
| `claude_code` | **Strict xfail** — stub until PR 15 |

Run locally:

```bash
cd adapter && uv run pytest -q tests/conformance
```
