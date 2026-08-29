# Voice Presentation Layer (VPL)

Extractive, **zero extra LLM** layered speech for long assistant replies.

## Problem

Hermes returns chat-optimized Markdown (often long numbered lists). Reading it all aloud fails for listening UX.

## Approach

1. **Dual channel:** `reply_full` unchanged on screen; TTS speaks short verbatim excerpts only.
2. **Parse** Markdown structure (headings, numbered items) — no model call.
3. **Bucket** items into 3–4 thematic groups when count exceeds threshold.
4. **FSM:** orient → map → deepen → done.
5. **Navigation intents** ("second", "bucket 2", "go back") advance FSM without calling Hermes.

## Public API

```python
from hcx_vpl import PresentationEngine, VplConfig

engine = PresentationEngine(VplConfig.from_env())
session, turn = engine.begin(full_markdown_text)
session, nav = engine.step(session, "second")
```

Modules: [parser.py](../../vpl/src/hcx_vpl/parser.py), [planner.py](../../vpl/src/hcx_vpl/planner.py), [renderer.py](../../vpl/src/hcx_vpl/renderer.py), [engine.py](../../vpl/src/hcx_vpl/engine.py), [intents.py](../../vpl/src/hcx_vpl/intents.py).

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `HCX_VPL_ENABLED` | `1` | Toggle layered delivery |
| `HCX_VPL_LAYER_THRESHOLD_ITEMS` | `5` | Min numbered items to layer |
| `HCX_VPL_MAX_BUCKETS` | `4` | Spoken bucket cap |
| `HCX_VPL_PASSTHROUGH_MAX_WORDS` | `400` | Short answers: speak all |
| `HCX_VPL_SESSION_TTL_SEC` | `1800` | Session expiry |

## Integration

- Wired in [voice/src/hcx_voice/server.py](../../voice/src/hcx_voice/server.py)
- VPL does **not** call Hermes or Cursor — voice sidecar owns backend calls

## Tests

- [vpl/tests/](../../vpl/tests/) — parser, intents, engine
- Fixture: [vpl/tests/fixtures/long_backlog.md](../../vpl/tests/fixtures/long_backlog.md) (16-item regression)

## Rules for agents

- Do not add LLM summarization inside VPL ([ADR 003](../decisions/003-vpl-zero-extra-llm.md)).
- Keep speech text extractive from source spans.
- Prefer extending parser/intents over growing monolithic engine logic.

## Related

- [voice-sidecar.md](voice-sidecar.md)
- [vpl/AGENTS.md](../../vpl/AGENTS.md)
- Package README: [vpl/README.md](../../vpl/README.md)
