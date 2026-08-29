# hcx-vpl — Voice Presentation Layer

Extractive, **zero extra LLM** layered speech from long assistant replies. Parses Markdown structure, buckets numbered items, and drives an orient → map → deepen navigation FSM with keyword/ordinal intents.

Hermes (or any text backend) returns the **full canonical answer**. VPL runs **after** that text is received. The screen shows `reply_full` unchanged; TTS speaks verbatim excerpts from source spans only.

## Install

```bash
cd vpl
pip install -e '.[dev]'
```

## Quick API

```python
from hcx_vpl import PresentationEngine, VplConfig

engine = PresentationEngine(VplConfig(enabled=True))
full_text = open("long_reply.md").read()

# New answer — may enter layered mode for long lists
session, turn = engine.begin(full_text)
print(turn.speak_text)   # short orient/map excerpt
print(turn.reply_full)   # full text (unchanged)
print(turn.buckets)      # [{id, label, count}, ...]

# Navigation turn — no backend call
if session:
    session, nav = engine.step(session, "second")
    print(nav.speak_text)
```

## Plug-and-play backend

VPL does not call Hermes. Wire any text-producing backend in your app:

```python
def ask_brain(prompt: str) -> str:
    return my_http_client.post("/chat", json={"q": prompt}).text

reply = ask_brain(user_text)
session, turn = engine.begin(reply)
```

The voice sidecar implements the Hermes-specific bridge in `voice/src/hcx_voice/hermes_bridge.py`.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `HCX_VPL_ENABLED` | `1` | Toggle layered delivery |
| `HCX_VPL_LAYER_THRESHOLD_ITEMS` | `5` | Min numbered items to layer |
| `HCX_VPL_MAX_BUCKETS` | `4` | Spoken bucket cap |
| `HCX_VPL_PASSTHROUGH_MAX_WORDS` | `400` | Short answers: speak all |
| `HCX_VPL_SESSION_TTL_SEC` | `1800` | Session expiry |

## Tests

```bash
pytest -q
```

Includes a 16-item regression fixture (`tests/fixtures/long_backlog.md`) for bucket chunking and FSM navigation.

## License

MIT — same as construct-zero / HCX.
