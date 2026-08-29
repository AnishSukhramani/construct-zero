# Feature registry

Status key: **MVP** = shipped in repo | **Stub** = placeholder only | **Out of scope** = do not build without explicit ask

| Feature | Status | Code | Doc |
|---------|--------|------|-----|
| HCX adapter (OpenAI façade) | MVP | [adapter/](../../adapter/) | [adapter-inference.md](adapter-inference.md) |
| Cursor tool passthrough | MVP | [adapter/src/hcx/core/sessions.py](../../adapter/src/hcx/core/sessions.py) | [adapter-inference.md](adapter-inference.md) |
| Hermes HCX provider plugin | MVP | [hermes-plugin/](../../hermes-plugin/) | [hermes-plugin.md](hermes-plugin.md) |
| Voice hold-to-talk sidecar | MVP | [voice/](../../voice/) | [voice-sidecar.md](voice-sidecar.md) |
| Voice Presentation Layer (VPL) | MVP | [vpl/](../../vpl/) | [voice-vpl.md](voice-vpl.md) |
| Claude Code driver | Stub | [adapter/src/hcx/drivers/claude_code.py](../../adapter/src/hcx/drivers/claude_code.py) | [adapter-inference.md](adapter-inference.md) |

## Out of scope (unless user explicitly requests)

- Depending on `cursor-api-proxy` as runtime
- Claude Code driver implementation (beyond stub)
- Public exposure of adapter port (must stay loopback)
- Cursor Cloud / iOS profiles
- Second agent brain inside HCX (Hermes owns tools)
- Vendoring Hermes source in this repo

## Nested agent entrypoints

When working inside a subsystem directory, Cursor also loads:

| Directory | AGENTS.md |
|-----------|-----------|
| `adapter/` | [adapter/AGENTS.md](../../adapter/AGENTS.md) |
| `voice/` | [voice/AGENTS.md](../../voice/AGENTS.md) |
| `vpl/` | [vpl/AGENTS.md](../../vpl/AGENTS.md) |
| `hermes-plugin/` | [hermes-plugin/AGENTS.md](../../hermes-plugin/AGENTS.md) |
