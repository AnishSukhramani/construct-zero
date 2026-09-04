# vpl/ — Voice Presentation Layer

Library: `construct-zero-vpl`. Extractive layered speech — **zero extra LLM calls**.

## Scope

- Parse Markdown → buckets → FSM (orient → map → deepen)
- Navigation intents without backend calls
- **Does not** call Hermes, Cursor, or HTTP

## Key files

| File | Role |
|------|------|
| `src/construct_zero_vpl/engine.py` | `PresentationEngine` |
| `src/construct_zero_vpl/parser.py` | Structure extraction |
| `src/construct_zero_vpl/intents.py` | Navigation detection |
| `src/construct_zero_vpl/planner.py` | Bucket planning |
| `src/construct_zero_vpl/renderer.py` | Speak text rendering |

## Public API

```python
from construct_zero_vpl import PresentationEngine, VplConfig
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
