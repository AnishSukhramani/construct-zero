# vpl/ — Voice Presentation Layer

Library: `hcx-vpl`. Extractive layered speech — **zero extra LLM calls**.

## Scope

- Parse Markdown → buckets → FSM (orient → map → deepen)
- Navigation intents without backend calls
- **Does not** call Hermes, Cursor, or HTTP

## Key files

| File | Role |
|------|------|
| `src/hcx_vpl/engine.py` | `PresentationEngine` |
| `src/hcx_vpl/parser.py` | Structure extraction |
| `src/hcx_vpl/intents.py` | Navigation detection |
| `src/hcx_vpl/planner.py` | Bucket planning |
| `src/hcx_vpl/renderer.py` | Speak text rendering |

## Public API

```python
from hcx_vpl import PresentationEngine, VplConfig
```

## Deep dive

[docs/features/voice-vpl.md](../docs/features/voice-vpl.md) · [ADR 003](../docs/decisions/003-vpl-zero-extra-llm.md)

## Tests

```bash
cd vpl && pytest -q
```

Fixture: `tests/fixtures/long_backlog.md`

## Rules

- Speech must stay verbatim from source spans
- No LLM summarization without new ADR
