# Data flow and ports

## Ports (loopback only)

| Service | Default host:port | Env overrides |
|---------|-------------------|---------------|
| HCX adapter | `127.0.0.1:8765` | `HCX_HOST`, `HCX_PORT` |
| Voice sidecar | `127.0.0.1:8767` | voice server config / scripts |

Both must remain on loopback unless the user explicitly changes deployment architecture.

## Adapter request flow

1. Hermes (or any OpenAI client) sends `POST /v1/chat/completions` to HCX.
2. [server.py](../../adapter/src/hcx/server.py) validates request, selects backend (`cursor` default).
3. [cursor.py](../../adapter/src/hcx/drivers/cursor.py) builds prompt, calls `cursor-sdk` with `mode=ask`.
4. If Hermes attached `tools`, driver exposes them as SDK `custom_tools`, **parks** tool calls, returns OpenAI `tool_calls`.
5. Hermes executes tools locally, posts tool results; session **resumes** the same Cursor run via [sessions.py](../../adapter/src/hcx/core/sessions.py).

HCX never executes terminal/web/skills — that is Hermes.

## Voice `/turn` flow

1. Browser POSTs audio to voice sidecar.
2. STT → transcript string.
3. If transcript is VPL **navigation intent** (e.g. "second", "go back") and session exists → VPL `engine.step()` only — **no Hermes call**.
4. Else → `ask_hermes(transcript)` subprocess (`hermes chat -q --provider hcx`).
5. VPL `engine.begin(reply)` → `speak_text` + full `reply_full`.
6. TTS synthesizes `speak_text`; JSON returns text + base64 audio.

## Config chain

```text
~/.hermes/config.yaml          model.provider: hcx, base_url: http://127.0.0.1:8765/v1
config/hermesxcursor.yaml      adapter bind, cursor.mode: ask
.env / CURSOR_API_KEY          Cursor billing
```

See [hermes-plugin.md](../features/hermes-plugin.md) and [adapter-inference.md](../features/adapter-inference.md).
