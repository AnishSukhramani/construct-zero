# voice/ — hold-to-talk sidecar

FastAPI on `127.0.0.1:8767`. STT + Hermes bridge + VPL + TTS.

## Scope

- Browser hold-to-talk UI (`static/`)
- `/turn` orchestration — not Hermes internals
- Depends on **construct-zero-vpl** ([vpl/](../vpl/)) for layered speech
- Depends on adapter `:8765` + Hermes CLI for brain calls

## Key files

| File | Role |
|------|------|
| `src/construct_zero_voice/server.py` | Endpoints, VPL wiring |
| `src/construct_zero_voice/hermes_bridge.py` | `hermes chat -q` subprocess |
| `src/construct_zero_voice/session_store.py` | VPL session TTL |
| `src/construct_zero_voice/stt_whisper.py` | STT |
| `src/construct_zero_voice/tts_kokoro.py` | TTS |

## Deep dives

- [docs/features/voice-sidecar.md](../docs/features/voice-sidecar.md)
- [docs/features/voice-vpl.md](../docs/features/voice-vpl.md)

## Tests

Mock backends via `set_backends()` — see `tests/test_turn.py`.

```bash
cd voice && pytest -q
```

## Invariants

- Do not spawn real Hermes in unit tests — mock `ask_hermes`
- Navigation intents skip Hermes when session active
