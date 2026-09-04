# Voice hold-to-talk sidecar

Browser push-to-talk on `127.0.0.1:8767`. Local STT + TTS; Hermes for reasoning via Construct-Zero.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | STT/TTS/Hermes/adapter status |
| POST | `/stt` | Speech-to-text (faster-whisper) |
| POST | `/tts` | Text-to-speech (Kokoro) |
| POST | `/turn` | Full pipeline: audio → Hermes → VPL → audio |
| POST | `/nav` | VPL navigation-only turn |
| GET | `/` | Static hold-to-talk UI |

## Pipeline (`/turn`)

1. STT transcript from uploaded audio.
2. If navigation intent + active VPL session → VPL step only (no Hermes).
3. Else `ask_hermes()` → subprocess `hermes chat -q --provider construct-zero --model auto`.
4. VPL `PresentationEngine.begin(reply)` → speak excerpt + full text.
5. TTS on `speak_text`; return JSON + base64 WAV.

## Key files

| File | Role |
|------|------|
| [server.py](../../voice/src/construct_zero_voice/server.py) | FastAPI, orchestration |
| [hermes_bridge.py](../../voice/src/construct_zero_voice/hermes_bridge.py) | Hermes CLI subprocess |
| [session_store.py](../../voice/src/construct_zero_voice/session_store.py) | VPL session TTL store |
| [stt_whisper.py](../../voice/src/construct_zero_voice/stt_whisper.py) | faster-whisper |
| [tts_kokoro.py](../../voice/src/construct_zero_voice/tts_kokoro.py) | Kokoro TTS |
| [static/](../../voice/src/construct_zero_voice/static/) | Hold-to-talk UI |

## Dependencies

- **construct-zero-vpl** ([vpl/](../../vpl/)) — layered speech after Hermes reply
- Adapter must be up on `:8765` for Hermes Construct-Zero provider
- Hermes binary: `.venvs/hermes/bin/hermes` (from `./scripts/setup.sh`)

## Env / setup

```bash
./scripts/setup-voice.sh
./scripts/start-voice.sh
# http://127.0.0.1:8767/
```

Requires `ffmpeg`; often `espeak-ng` for Kokoro.

## Tests

Mocked STT/TTS/Hermes — no model download in pytest. Uses `set_backends()` hook in [server.py](../../voice/src/construct_zero_voice/server.py).

```bash
cd voice && pytest -q
```

## Related

- [voice-vpl.md](voice-vpl.md)
- [voice/AGENTS.md](../../voice/AGENTS.md)
